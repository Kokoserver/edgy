from typing import ClassVar

import edgy
from edgy import Database, Manager, QuerySet, Registry

database = Database("sqlite:///db.sqlite")
models = Registry(database=database)


class InactiveManager(Manager):
    """
    Custom manager that will return only active users
    """

    def get_queryset(self) -> "QuerySet":
        queryset = super().get_queryset().filter(is_active=False)
        return queryset


class User(edgy.Model):
    name: str = edgy.CharField(max_length=255)
    email: str = edgy.EmailField(max_length=70)
    is_active: bool = edgy.BooleanField(default=True)

    # Add the new manager
    inactives: ClassVar[Manager] = InactiveManager()

    class Meta:
        registry = models
        unique_together = ["name", "email"]


# Using ipython that supports await
# Don't use this in production! Use Alembic or any tool to manage
# The migrations for you
await models.create_all()  # noqa

# Create an inactive user
await User.query.create(name="Edgy", email="foo@bar.com", is_active=False)  # noqa

# You can also create a user using the new manager
await User.inactives.create(name="Another Edgy", email="bar@foo.com", is_active=False)  # noqa

# Querying using the new manager
user = await User.inactives.get(email="foo@bar.com")  # noqa
# User(id=1)

user = await User.inactives.get(email="bar@foo.com")  # noqa
# User(id=2)

# Create a user using the default manager
await User.query.create(name="Edgy", email="user@edgy.com")  # noqa

# Querying all inactives only
users = await User.inactives.all()  # noqa
# [User(id=1), User(id=2)]

# Querying them all
user = await User.query.all()  # noqa
# [User(id=1), User(id=2), User(id=3)]
