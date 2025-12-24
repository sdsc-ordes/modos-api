# Key Management Service (KMS)

The kms coordinates the identity provider and S3 server to issue temporary S3 credentials that correspond to JWT tokens delivered by the identity provider.

This allows the client to transparently request and refresh those credentials as long as it has a valid JWT from the identity provider.

>[!IMPORTANT]
> The KMS is only required when authentication is needed. To enable it, use `docker compose --profile auth [...]`. It requires an external identity provider to function, and only supports authentik and garage S3.

```mermaid
sequenceDiagram
    participant C as Client
    participant IdP as Identity Provider
    participant KMS as Key Management Service
    participant S3 as S3 Server

    C->>IdP: Login (device code flow)
    activate IdP
    IdP-->>C: JWT token
    deactivate IdP

    C->>KMS: Request S3 access key (with JWT)
    activate KMS
    KMS->>KMS: Validate JWT
    KMS->>S3: Request new access key (match JWT lifetime & permissions)
    activate S3
    S3-->>KMS: Return S3 access key
    deactivate S3
    KMS-->>C: Return S3 access key
    deactivate KMS

    C->>C: Persist S3 access key
```
