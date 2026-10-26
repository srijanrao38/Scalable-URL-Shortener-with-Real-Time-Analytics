# EC2 deployment

## GitHub secrets

Create these repository secrets:

| Secret | Purpose |
| --- | --- |
| `EC2_HOST` | Public DNS name or IP of the EC2 instance |
| `EC2_USER` | SSH user, such as `ubuntu` |
| `EC2_SSH_KEY` | Private key matching the instance's authorized public key |
| `EC2_APP_DIR` | Optional remote directory; defaults to `/opt/link-shotner` |
| `POSTGRES_PASSWORD` | Strong PostgreSQL password |
| `DATABASE_URL` | Production SQLAlchemy URL containing the PostgreSQL password |
| `BASE_URL` | Public short-link origin, such as `https://short.example` |
| `IP_HASH_SALT` | Long random salt used to hash client IPs |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |

The deployment workflow writes `/opt/link-shotner/.env` from these secrets
over SSH. It is never committed or copied from the source checkout.

## Prepare the EC2 instance

1. Launch an Ubuntu EC2 instance and attach a security group.
2. Install Docker Engine and the Docker Compose plugin using Docker's official
   Ubuntu instructions.
3. Create the application directory and give the SSH user ownership:

   ```bash
   sudo mkdir -p /opt/link-shotner
   sudo chown "$USER":"$USER" /opt/link-shotner
   ```

4. Add the deployment public key to `~/.ssh/authorized_keys` and verify that
   `ssh <user>@<host>` works.
5. The first deployment creates `.env` from GitHub Secrets. If you need to
   create it manually for a dry run, copy `.env.example`, replace local values,
   and keep the file readable only by the deployment user:

   ```bash
   chmod 600 /opt/link-shotner/.env
   ```

6. Allow only TCP 80 (HTTP) and TCP 443 (HTTPS, if TLS is added later) from
   the internet. Do not expose PostgreSQL or Redis. SSH (TCP 22) should be
   limited to your administration IP range.

The workflow backs up the previous source release, copies the application,
builds the images on EC2, runs Alembic, starts Compose, and checks
`http://localhost/health` before succeeding.

## Roll back a bad deploy

SSH to the instance and list the backups:

```bash
ls -1dt /opt/link-shotner/backups/*
```

Restore the newest known-good backup (replace the timestamp):

```bash
cd /opt/link-shotner
docker compose down
cp -a backups/<timestamp>/. .
docker compose build
docker compose up -d
curl --fail http://localhost/health
```

Database migrations are forward-only in this project. If a bad release
changed the schema, restore the database from your normal PostgreSQL backup
before running an older application image.
