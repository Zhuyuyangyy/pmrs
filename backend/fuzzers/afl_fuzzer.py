"""
AFL++ Fuzzer Wrapper
AFL++模糊测试执行器 - 通过wrapper方式集成，不修改AFL++源码
"""
import asyncio
import subprocess
import os
import json
import time
import signal
import logging
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from datetime import datetime
import hashlib

from core.config import settings

logger = logging.getLogger(__name__)


class AFLFuzzer:
    """AFL++模糊测试包装器"""

    def __init__(self, target_ip: str = "127.0.0.1", target_port: int = 502):
        self.target_ip = target_ip
        self.target_port = target_port
        self.afl_path = settings.AFL_PATH
        self.input_dir = settings.AFL_INPUT_DIR
        self.output_dir = settings.AFL_OUTPUT_DIR
        self.timeout = settings.AFL_TIMEOUT
        
        # 确保目录存在
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def create_harness(self, protocol: str) -> str:
        """生成AFL++测试工具（harness）
        
        创建一个用C编写的轻量级harness，用于AFL++模糊测试
        这个harness负责接收模糊输入并发送到目标服务器
        """
        harnesses = {
            "modbus_tcp": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <signal.h>

#define TARGET_IP "{target_ip}"
#define TARGET_PORT {target_port}
#define TIMEOUT_MS 1000

volatile sig_atomic_t timeout_flag = 0;

void timeout_handler(int sig) {{
    timeout_flag = 1;
}}

int connect_target() {{
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(TARGET_PORT);
    inet_pton(AF_INET, TARGET_IP, &addr.sin_addr);
    
    struct timeval tv;
    tv.tv_sec = TIMEOUT_MS / 1000;
    tv.tv_usec = (TIMEOUT_MS % 1000) * 1000;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    
    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {{
        close(sock);
        return -1;
    }}
    return sock;
}}

int main(int argc, char** argv) {{
    if (argc < 2) {{
        fprintf(stderr, "Usage: %s <input_file>\n", argv[0]);
        return 1;
    }}
    
    FILE* f = fopen(argv[1], "rb");
    if (!f) return 1;
    
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    char* buf = malloc(len + 1);
    fread(buf, 1, len, f);
    fclose(f);
    
    int sock = connect_target();
    if (sock < 0) return 1;
    
    signal(SIGALRM, timeout_handler);
    alarm(TIMEOUT_MS / 1000 + 1);
    
    send(sock, buf, len, 0);
    
    char resp[1024];
    int n = recv(sock, resp, sizeof(resp), 0);
    
    close(sock);
    free(buf);
    
    if (timeout_flag) return 2; // Timeout
    return 0;
}}
""",
            "generic": r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

#define TARGET_IP "{target_ip}"
#define TARGET_PORT {target_port}

int main(int argc, char** argv) {{
    if (argc < 2) return 1;
    
    FILE* f = fopen(argv[1], "rb");
    if (!f) return 1;
    
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    char* buf = malloc(len);
    fread(buf, 1, len, f);
    fclose(f);
    
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(TARGET_PORT);
    inet_pton(AF_INET, TARGET_IP, &addr.sin_addr);
    
    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) == 0) {{
        send(sock, buf, len, 0);
        char resp[1024];
        recv(sock, resp, sizeof(resp), 0);
    }}
    
    close(sock);
    free(buf);
    return 0;
}}
"""
        }
        
        code = harnesses.get(protocol, harnesses["generic"])
        return code.format(target_ip=self.target_ip, target_port=self.target_port)

    async def compile_harness(self, protocol: str, work_dir: str) -> Optional[str]:
        """编译harness为可执行文件"""
        code = self.create_harness(protocol)
        harness_path = os.path.join(work_dir, "harness.c")
        binary_path = os.path.join(work_dir, "harness")
        
        with open(harness_path, "w") as f:
            f.write(code)
        
        # 使用AFL++编译
        cmd = [
            "afl-gcc-fast",
            harness_path,
            "-o",
            binary_path,
            "-static",
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=work_dir
            )
            if result.returncode == 0 and os.path.exists(binary_path):
                return binary_path
            logger.error(f"Compilation failed: {result.stderr}")
            return None
        except Exception as e:
            logger.error(f"Compilation error: {e}")
            return None

    async def write_testcase(self, testcase_hex: str, case_id: int) -> str:
        """将测试用例（十六进制）写入文件"""
        try:
            data = bytes.fromhex(testcase_hex.replace(" ", ""))
            filepath = os.path.join(self.input_dir, f"id:{case_id:06d}")
            with open(filepath, "wb") as f:
                f.write(data)
            return filepath
        except Exception as e:
            logger.error(f"Failed to write testcase: {e}")
            return ""

    async def run_fuzzing(
        self,
        protocol: str,
        duration: int = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """运行AFL++模糊测试"""
        duration = duration or self.timeout
        
        # 创建临时工作目录
        work_dir = os.path.join(self.output_dir, f"fuzz_{int(time.time())}")
        os.makedirs(work_dir, exist_ok=True)
        
        # 编译harness
        harness_path = await self.compile_harness(protocol, work_dir)
        if not harness_path:
            return {"status": "error", "message": "Failed to compile harness"}
        
        # 准备初始测试用例（如果存在）
        initial_seed = os.path.join(work_dir, "seed")
        os.makedirs(initial_seed, exist_ok=True)
        
        # 运行AFL++
        cmd = [
            "afl-fuzz",
            "-i", initial_seed,
            "-o", self.output_dir,
            "-f", "input.bin",
            "--",
            harness_path,
            "@@",  # AFL++会用输入文件替换@@
        ]
        
        # 设置环境变量
        env = os.environ.copy()
        env["AFL_SKIP_CPUFREQ"] = "1"
        env["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = "1"
        
        result = {
            "status": "running",
            "work_dir": work_dir,
            "started_at": datetime.utcnow().isoformat(),
            "crashes": [],
            "stats": {},
        }
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            # 监控进度
            start_time = time.time()
            while process.returncode is None:
                if duration and (time.time() - start_time) >= duration:
                    process.send_signal(signal.SIGINT)
                    await asyncio.sleep(1)
                    if process.returncode is None:
                        process.kill()
                    break
                
                if progress_callback:
                    await progress_callback({
                        "elapsed": time.time() - start_time,
                        "duration": duration,
                        "progress": min(100, (time.time() - start_time) / duration * 100),
                    })
                
                await asyncio.sleep(5)
            
            # 收集结果
            result["crashes"] = await self._collect_crashes(work_dir)
            result["stats"] = await self._parse_stats(work_dir)
            result["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Fuzzing error: {e}")
            result["status"] = "error"
            result["message"] = str(e)
        
        return result

    async def _collect_crashes(self, work_dir: str) -> List[Dict[str, Any]]:
        """收集崩溃用例"""
        crashes = []
        crash_dir = os.path.join(work_dir, "default", "crashes")
        
        if not os.path.exists(crash_dir):
            return crashes
        
        for fname in os.listdir(crash_dir):
            if fname.startswith("id:"):
                fpath = os.path.join(crash_dir, fname)
                with open(fpath, "rb") as f:
                    data = f.read()
                
                crashes.append({
                    "id": fname,
                    "input_hex": data.hex(),
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                })
        
        return crashes

    async def _parse_stats(self, work_dir: str) -> Dict[str, Any]:
        """解析AFL++统计信息"""
        stats_file = os.path.join(work_dir, "default", "fuzzer_stats")
        stats = {}
        
        if os.path.exists(stats_file):
            with open(stats_file) as f:
                for line in f:
                    if ":" in line:
                        key, value = line.strip().split(":", 1)
                        stats[key.strip()] = value.strip()
        
        return stats

    async def stop(self):
        """停止模糊测试"""
        # 查找并终止afl-fuzz进程
        try:
            subprocess.run(["pkill", "-f", "afl-fuzz"], capture_output=True)
        except:
            pass


class CrashMonitor:
    """崩溃监控器 - 实时监控目标程序的崩溃/异常"""

    def __init__(self):
        self.active_monitors: Dict[int, asyncio.Task] = {}

    async def monitor_process(
        self,
        pid: int,
        callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """监控指定进程的崩溃"""
        crash_info = {
            "pid": pid,
            "signals": [],
            "start_time": datetime.utcnow().isoformat(),
        }
        
        try:
            # 使用timeout命令监控进程退出
            proc = await asyncio.create_subprocess_exec(
                "timeout", "3600",
                "strace", "-p", str(pid),
                "-e", "trace=none",
                "-s", "100",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self.active_monitors[pid] = proc
            
            try:
                await asyncio.wait_for(proc.wait(), timeout=3600)
            except asyncio.TimeoutError:
                proc.kill()
            
        except ProcessLookupError:
            crash_info["signals"].append({
                "signal": "SIGCHLD",
                "info": "Process terminated",
                "time": datetime.utcnow().isoformat(),
            })
        
        if callback:
            await callback(crash_info)
        
        return crash_info

    def stop_monitor(self, pid: int):
        """停止监控"""
        if pid in self.active_monitors:
            self.active_monitors[pid].cancel()
            del self.active_monitors[pid]


# 全局实例
crash_monitor = CrashMonitor()
