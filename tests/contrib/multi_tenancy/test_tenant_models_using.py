from datetime import datetime

import pytest
from tests.settings import DATABASE_URL

from edgy.contrib.multi_tenancy import TenantModel, TenantRegistry
from edgy.contrib.multi_tenancy.models import TenantMixin
from edgy.core.db import fields
from edgy.testclient import DatabaseTestClient as Database

database = Database(url=DATABASE_URL)
models = TenantRegistry(database=database)

pytestmark = pytest.mark.anyio


def time():
    return datetime.now().time()


@pytest.fixture(autouse=True, scope="module")
async def create_test_database():
    try:
        await models.create_all()
        yield
        await models.drop_all()
    except Exception as e:
        pytest.skip(f"Error: {str(e)}")


@pytest.fixture(autouse=True)
async def rollback_connections():
    with database.force_rollback():
        async with database:
            yield


async def drop_schemas(name):
    await models.schema.drop_schema(name, if_exists=True)


class Tenant(TenantMixin):
    class Meta:
        registry = models


class User(TenantModel):
    id: int = fields.IntegerField(primary_key=True)
    name: str = fields.CharField(max_length=255)

    class Meta:
        registry = models
        is_tenant = True


class Product(TenantModel):
    id: int = fields.IntegerField(primary_key=True)
    name: str = fields.CharField(max_length=255)
    user: User = fields.ForeignKey(User, null=True)

    class Meta:
        registry = models
        is_tenant = True


async def test_schema_with_using_in_different_place():
    tenant = await Tenant.query.create(
        schema_name="edgy", domain_url="https://edgy.tarsild.io", tenant_name="edgy"
    )

    for i in range(5):
        await Product.query.using(tenant.schema_name).create(name=f"product-{i}")

    total = await Product.query.filter().using(tenant.schema_name).all()

    assert len(total) == 5

    total = await Product.query.all()

    assert len(total) == 0

    for i in range(15):
        await Product.query.create(name=f"product-{i}")

    total = await Product.query.all()

    assert len(total) == 15

    total = await Product.query.filter().using(tenant.schema_name).all()

    assert len(total) == 5


async def test_can_have_multiple_tenants_with_different_records_with_using():
    edgy = await Tenant.query.create(
        schema_name="edgy", domain_url="https://edgy.tarsild.io", tenant_name="edgy"
    )
    saffier = await Tenant.query.create(
        schema_name="saffier", domain_url="https://saffier.tarsild.io", tenant_name="saffier"
    )

    # Create a user for edgy
    user_edgy = await User.query.only().using(edgy.schema_name).create(name="Edgy")

    # Create products for user_edgy
    for i in range(5):
        await Product.query.defer().using(edgy.schema_name).create(
            name=f"product-{i}", user=user_edgy
        )

    # Create a user for saffier
    user_saffier = await User.query.group_by().using(saffier.schema_name).create(name="Saffier")

    # Create products for user_saffier
    for i in range(25):
        await Product.query.exclude().using(saffier.schema_name).create(
            name=f"product-{i}", user=user_saffier
        )

    # Create top level users
    for name in range(10):
        await User.query.filter().using(saffier.schema_name).create(name=f"user-{name}")
        await User.query.filter().using(edgy.schema_name).create(name=f"user-{name}")
        await User.query.distinct().create(name=f"user-{name}")

    # Check the totals
    top_level_users = await User.query.all()
    assert len(top_level_users) == 10

    users_edgy = await User.query.using(edgy.schema_name).all()
    assert len(users_edgy) == 11

    users_saffier = await User.query.using(saffier.schema_name).all()
    assert len(users_saffier) == 11
