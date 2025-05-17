# Codegen Examples

[![Documentation](https://img.shields.io/badge/docs-docs.codegen.com-blue)](https://docs.codegen.com)

This is a collection of examples using [Codegen](https://codegen.com). You can use these examples to learn how to use Codegen and integrate the codegen agent into your workflows.

## Setup

We recommend using [`uv`](https://github.com/astral-sh/uv) with Python 3.13 for the best experience.

Install Codegen
```bash
uv pip install codegen
```

In order to use the codegen API you will need to generate a token [here](https://www.codegen.sh/token)

Your environment is now ready to use the codegen API!

## Examples

Within the examples folder, each subdirectory contains a self-contained example with:
- An explanation of the use case (`README.md`)
- Files that leverage codegen for powerful applications

### Available Examples

1. **Agent Tasks** - Examples of using the `Agent` class to create and run AI-powered agents
2. **Codebase Analysis** - Examples of using the `Codebase` class to analyze and manipulate code
3. **Custom Functions** - Examples of using the `function` decorator and `CodegenApp` class
4. **Codecov Agent Trigger** - Example of integrating Codegen with Codecov

For a detailed overview of all examples, see [examples.md](examples.md).

## Learn More

- [Documentation](https://docs.codegen.com)
- [API](https://docs.codegen.com/introduction/api)
- [Agent Capabilities](https://docs.codegen.com/introduction/capabilities)
- [Prompting](https://docs.codegen.com/introduction/prompting)
- [Community](https://docs.codegen.com/introduction/community)


## Contributing

Have a useful example to share? We'd love to include it! Please see our [Contributing Guide](CONTRIBUTING.md) for instructions.

## License

The [Apache 2.0 license](LICENSE).
