# PMRS Development Roadmap

## Current Version: 1.0.0

---

## Phase 1: Core Stability (v1.1.0) - Q2 2026

### Bug Fixes
- [x] Fix CVSS calculator `privilegesrequired` typo in `build_vector()`
- [x] Fix Chinese characters in `calculate_from_crash()` parameter names
- [x] Implement IEC 61850 protocol module (was empty)
- [x] Implement DNP3 protocol module (was empty)
- [x] Fix `api/protocols.py` import for IEC61850 and DNP3 classes
- [ ] Fix `api/projects.py` missing `create_project()` method on VulnerabilityScanner

### Testing
- [x] Create shared test fixtures (`conftest.py`)
- [x] Add comprehensive API schema validation tests
- [x] Add LLM service unit tests
- [x] Add scanner service unit tests
- [x] Add security middleware tests
- [x] Add configuration tests
- [x] Add fuzzer wrapper tests
- [ ] Add API endpoint integration tests with httpx.AsyncClient
- [ ] Add database integration tests
- [ ] Achieve 80%+ test coverage

### Documentation
- [x] Create API Reference documentation
- [x] Create Architecture Guide
- [x] Create Protocol Implementation Guide
- [x] Create Security Policy document
- [x] Enhance README with badges, table of contents, testing section

---

## Phase 2: Smart Resource Scheduling (v1.2.0) - Q3 2026

### Intelligent Resource Scheduling
- [ ] **Adaptive Scan Scheduling** - Automatically schedule scans based on target availability windows
- [ ] **Resource Pool Management** - Manage AFL++ worker nodes with automatic scaling
- [ ] **Priority Queue** - Priority-based scan queue with preemption for critical targets
- [ ] **Load Balancing** - Distribute fuzzing workloads across multiple AFL++ instances
- [ ] **Resource Quotas** - Per-project resource limits and fair-share scheduling

### Implementation Details
```
SmartScheduler
├── ResourceMonitor       # Track CPU, memory, network usage
├── PriorityQueue         # Priority-based task scheduling
├── LoadBalancer          # Distribute work across workers
├── AdaptiveScheduler     # ML-based scheduling optimization
└── QuotaManager          # Per-project resource quotas
```

---

## Phase 3: Project Risk Prediction (v1.3.0) - Q4 2026

### AI-Powered Risk Assessment
- [ ] **Vulnerability Prediction Model** - ML model to predict vulnerability likelihood by protocol/function
- [ ] **Risk Scoring Dashboard** - Real-time risk scores for each project
- [ ] **Historical Analysis** - Trend analysis of vulnerability discovery patterns
- [ ] **Attack Surface Mapping** - Automatic mapping of exposed attack surfaces
- [ ] **Risk Heatmaps** - Visual risk heatmaps by protocol, function, and severity

### Implementation Details
```
RiskPredictor
├── FeatureExtractor      # Extract features from protocol/code analysis
├── VulnerabilityModel    # Trained ML model for vulnerability prediction
├── RiskScorer            # Composite risk scoring engine
├── TrendAnalyzer         # Historical trend analysis
└── AttackSurfaceMapper   # Automatic attack surface discovery
```

---

## Phase 4: Progress Auto-Tracking (v1.4.0) - Q1 2027

### Automated Progress Monitoring
- [ ] **Real-time Scan Progress** - WebSocket-based live progress updates
- [ ] **Milestone Detection** - Automatic detection of scan milestones (first crash, coverage targets)
- [ ] **Anomaly Detection** - Detect unusual patterns during fuzzing (stuck scans, regression)
- [ ] **Auto-reporting** - Automated scan reports with key findings
- [ ] **Progress Predictions** - ML-based scan completion time predictions

### Implementation Details
```
ProgressTracker
├── WebSocketManager      # Real-time client updates
├── MilestoneDetector     # Automatic milestone recognition
├── AnomalyDetector       # Unusual pattern detection
├── ReportGenerator       # Automated report generation
└── CompletionPredictor   # ML-based time predictions
```

---

## Phase 5: Multi-Project Collaboration (v1.5.0) - Q2 2027

### Multi-Project Orchestration
- [ ] **Cross-Project Correlation** - Correlate vulnerabilities across related projects
- [ ] **Shared Knowledge Base** - Shared protocol knowledge across team projects
- [ ] **Collaborative Scanning** - Multiple users can contribute to the same scan
- [ ] **Project Templates** - Reusable project templates for common ICS configurations
- [ ] **Dependency Mapping** - Map dependencies between projects and protocols

### Implementation Details
```
MultiProjectOrchestrator
├── CorrelationEngine     # Cross-project vulnerability correlation
├── KnowledgeBase         # Shared protocol/vulnerability knowledge
├── CollaborativeScanner  # Multi-user scan collaboration
├── TemplateManager       # Project template CRUD
└── DependencyMapper      # Project dependency graph
```

---

## Phase 6: Advanced Fuzzing (v2.0.0) - Q3 2027

### Next-Generation Fuzzing
- [ ] **Grammar-Based Fuzzing** - Protocol grammar-aware test generation
- [ ] **Differential Fuzzing** - Compare behavior across protocol implementations
- [ ] **Hybrid Fuzzing** - Combine symbolic execution with fuzzing
- [ ] **Protocol Reverse Engineering** - Automatic protocol reverse engineering from traffic
- [ ] **Smart Seed Selection** - ML-based seed selection for maximum coverage

### New Protocol Support
- [ ] **PROFINET** - Industrial Ethernet protocol
- [ ] **EtherNet/IP** - CIP-based industrial protocol
- [ ] **OPC UA** - Unified Architecture for industrial interoperability
- [ ] **BACnet** - Building automation protocol
- [ ] **IEC 60870-5-104** - Telecontrol protocol

---

## Innovation Areas

### Smart Resource Scheduling
Automatically allocate fuzzing resources based on target priority, historical vulnerability density, and available compute capacity. Uses reinforcement learning to optimize scheduling decisions.

### Project Risk Prediction
ML models trained on historical vulnerability data to predict which protocol functions are most likely to contain vulnerabilities. Enables proactive security testing.

### Progress Auto-Tracking
Real-time monitoring with anomaly detection to identify stuck scans, regression, and unusual patterns. Automated reporting keeps stakeholders informed.

### Multi-Project Collaboration
Cross-project vulnerability correlation identifies systemic issues. Shared knowledge bases accelerate new project setup.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

This project is released under the MIT License.
