import edgy

# Create some records

await User.query.create(name="Adam", email="adam@edgy.dev")
await User.query.create(name="Eve", email="eve@edgy.dev")

# Query using the and_
await User.query.filter(name="Adam").and_(email="adam@edgy.dev")
