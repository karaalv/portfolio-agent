# Process-local client state

The application assumes one active instance of each service client per Python
process. Each client's package holds its client in module state, and package
functions use that instance. This assumption applies regardless of when a
particular client is initialised.

Running Uvicorn with more than one worker is compatible with this model. Each
worker is a separate process with its own module state and its own client
instance. Clients are not shared between workers.

The unsafe case is running multiple application instances in the **same
process** while they initialise or replace the same module-level client. For
example, a test app that installs a test client while a live app is running in
that process could redirect the live app's database calls to the test client.
Test teardown could also close the client the live app expects to use. A test
running in a separate process cannot replace the live process's module state.

If the application ever needs concurrent app instances or differently
configured clients within one process, this assumption must be revisited. Give
each app ownership of its client and pass the correct client to code that needs
it, for example through app state and dependency injection.
