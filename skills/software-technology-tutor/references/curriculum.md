# Curriculum — Software Technology Tutor

Reference for `SKILL.md` section 3. Read the domain that matches the learner's question;
use the lists to find prerequisites and related concepts, not as a lecture order.

## Contents

- Domain 1: Software fundamentals
- Domain 2: Client-server systems
- Domain 3: APIs and integration
- Domain 4: Databases and data
- Domain 5: Software architecture
- Domain 6: Web and mobile applications
- Domain 7: Infrastructure and deployment
- Domain 8: Security and reliability

Organize learning into the following domains. Adapt the order to the learner's current question and knowledge.

### Domain 1: Software fundamentals

Teach:
- What software is.
- What a software application is.
- Program, process, and thread.
- Source code, compiler, interpreter, and runtime.
- Programming language versus framework versus library.
- SDK, package, dependency, and package manager.
- Operating system and system calls.
- Memory, files, and processes.
- Build time versus runtime.

### Domain 2: Client-server systems

Teach:
- Client and server.
- Frontend and backend.
- Request-response communication.
- Web server and application server.
- Server process versus physical server.
- Localhost, IP address, port, domain, and DNS.
- TCP, UDP, HTTP, and HTTPS.
- Latency, bandwidth, and timeout.
- Reverse proxy and load balancer.
- Stateless versus stateful services.

Explain which components are logical roles and which are physical or executable resources.

### Domain 3: APIs and integration

Teach:
- What an API is and why it exists.
- API contract and interface.
- HTTP API and REST.
- URL, URI, endpoint, and HTTP method.
- Request headers, query parameters, path parameters, and body.
- Response status codes, headers, and body.
- JSON and serialization.
- Authentication versus authorization.
- API key, session, and token.
- Rate limiting, pagination, and versioning.
- Webhooks and polling.
- SDKs and third-party integrations.
- Error handling and API documentation.

Use concrete request-response examples when appropriate.

Clearly distinguish a simplified illustrative example from a production-ready implementation.

### Domain 4: Databases and data

Teach:
- Data versus information.
- Database versus DBMS.
- Relational and non-relational databases.
- Table, row, column, primary key, and foreign key.
- SQL and database drivers.
- Database connection and connection pool.
- Transactions and ACID.
- Indexes and query performance.
- Normalization and denormalization.
- Cache and database.
- Replication, backup, and recovery.
- Data consistency and concurrency.

Explain why applications often access databases through a backend rather than allowing every client to connect directly.

### Domain 5: Software architecture

Teach:
- Requirements and system boundaries.
- Monolith and microservices.
- Layered architecture.
- Presentation, application, domain, and infrastructure layers.
- MVC and other relevant architectural patterns.
- Separation of concerns.
- Dependency injection.
- Coupling and cohesion.
- Domain models and data models.
- Message queues and asynchronous processing.
- Event-driven architecture.
- Scalability, availability, and fault tolerance.
- Architectural trade-offs.

Do not recommend microservices automatically. Explain why a modular monolith can be more appropriate for a small team or early-stage product.

### Domain 6: Web and mobile applications

Teach:
- Browser and rendering.
- HTML, CSS, and JavaScript.
- SPA and traditional server-rendered applications.
- Mobile application and web application.
- Native, hybrid, and cross-platform applications.
- Application state and persistent storage.
- Cookies, sessions, and local storage.
- CORS and browser security boundaries.
- Authentication flows.
- Push notifications and background processing.

Explain the difference between what runs on a user's device and what runs on a remote server.

### Domain 7: Infrastructure and deployment

Teach:
- Development, testing, staging, and production environments.
- Git and version control.
- Build artifacts and deployment.
- Hosting and cloud computing.
- Virtual machines and containers.
- Docker and container images.
- Environment variables and secrets.
- CI/CD.
- Logs, metrics, tracing, and monitoring.
- Domain names, DNS records, and TLS certificates.
- Horizontal and vertical scaling.
- Backups, rollback, and disaster recovery.

Explain how code moves from a developer's machine to a system used by real customers.

### Domain 8: Security and reliability

Teach:
- Authentication and authorization.
- Least privilege.
- Input validation and output encoding.
- SQL injection and parameterized queries.
- Password hashing.
- Encryption in transit and at rest.
- Secret management.
- Access control.
- Audit logs.
- Idempotency and retry behavior.
- Timeouts, circuit breakers, and graceful failure.
- Security boundaries between client, server, and database.

Use defensive, educational examples and emphasize practical engineering principles.
