import sys
import uuid
import datetime
sys.path.append("src")
from guardian_lens.core.settings import load_settings
from guardian_lens.tenancy.registry import TenantRegistry
from guardian_lens.tenancy.router import TenantRouter
from guardian_lens.repositories.camera_discovery import CameraDiscoveryRepository
import sqlalchemy as sa

settings = load_settings()
registry = TenantRegistry(settings.control_db_url)
router = TenantRouter(registry, settings.tenant_db_url)

# Find an existing tenant and site
with registry._engine.connect() as conn:
    tenant_slug = conn.execute(sa.text("SELECT slug FROM tenants LIMIT 1")).scalar()

with router.bind(tenant_slug) as context:
    site_id = context.session.execute(sa.text("SELECT id FROM sites LIMIT 1")).scalar()
    print("Testing with site:", site_id)
    
    repo = CameraDiscoveryRepository(context.session)
    scan_id = uuid.uuid4()
    try:
        scan = repo.create_scan(scan_id, site_id)
        print("Create scan succeeded:", scan)
    except Exception as e:
        print("Create scan failed:", e)
        
    try:
        scan2 = repo.get_scan(scan_id)
        print("Get scan succeeded:", scan2)
    except Exception as e:
        print("Get scan failed:", e)
