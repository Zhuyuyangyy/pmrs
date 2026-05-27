-- PMRS 数据库初始化脚本
-- 首次启动时自动执行

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 可以在这里添加初始化表结构或其他初始配置
-- 例如：
-- CREATE TABLE IF NOT EXISTS projects (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     name VARCHAR(255) NOT NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- 创建索引 (可选优化)
-- CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

-- 完成
DO $$
BEGIN
    RAISE NOTICE 'PMRS database initialized successfully';
END $$;