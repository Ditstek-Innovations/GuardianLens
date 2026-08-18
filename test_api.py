import sys
import uuid
import datetime
import asyncio
from sqlalchemy import text
sys.path.append("src")
from guardian_lens.core.settings import load_settings
from guardian_lens.tenancy.registry import TenantRegistry
from guardian_lens.tenancy.router import TenantRouter

settings = load_settings()
registry = TenantRegistry(settings.control_db_url)

# Mint a token for a user
with registry._engine.connect() as conn:
    tenant_slug = conn.execute(text("SELECT slug FROM tenants LIMIT 1")).scalar()
    
# We need an access token. Since we're in the workspace, we can just use the auth module directly to mint one.
from guardian_lens.services.auth import AuthService
from guardian_lens.core.principal import HumanPrincipal

# Let's bypass HTTP and just call the router functions directly!
from guardian_lens.api.routes.discovery import start_discovery_scan, get_scan_status
from guardian_lens.tenancy.context import TenantContext
from fastapi import BackgroundTasks

async def test_api():
    router = TenantRouter(registry, settings.tenant_db_url)
    with router.bind(tenant_slug) as context:
        site_id = context.session.execute(text("SELECT id FROM sites LIMIT 1")).scalar()
        principal = HumanPrincipal(
            user_id=uuid.uuid4(),
            tenant_slug=tenant_slug,
            tenant_id=context.tenant_id,
            email="test@example.com",
            roles=["SITE_ADMIN"]
        )
        class MockRequest:
            client = type('Client', (), {'host': '127.0.0.1'})
            app = type('App', (), {'state': type('State', (), {'credential_sealer': None})})
            
        bg = BackgroundTasks()
        
        # Test POST
        print("Starting scan...")
        resp = await start_discovery_scan(
            subnet="192.168.1.0/24",
            site_id=site_id,
            background_tasks=bg,
            request=MockRequest(),
            principal=principal,
            context=context
        )
        print("Scan created:", resp.id)
        
        # Test GET
        print("Fetching scan status...")
        try:
            status_resp = await get_scan_status(
                scan_id=resp.id,
                principal=principal,
                context=context
            )
            print("Scan status:", status_resp.status)
        except Exception as e:
            print("Failed to get scan status:", e)

if __name__ == "__main__":
    asyncio.run(test_api())
