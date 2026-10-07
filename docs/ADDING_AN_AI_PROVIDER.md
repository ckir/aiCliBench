# Adding an AI Provider

1. Implement the provider adapter in `packages/integrations/<provider>`.
2. Depend on the `ai` abstraction.
3. Keep provider SDK types inside the adapter.
4. Normalize errors into product-level errors.
5. Support explicit timeouts.
6. Provide a fake/mock transport for tests.
7. Add provider-specific integration tests.
8. Add optional live tests guarded by environment/configuration.
9. Document supported model capabilities.
10. Never require live provider credentials for ordinary PR CI.
