"""Tests for the composition-root entrypoint in src.main."""

from __future__ import annotations

from types import ModuleType

import pytest


class _StubHandlerRegistrar:
    def __init__(self, *, raise_import_error: bool = False) -> None:
        self.called = 0
        self.raise_import_error = raise_import_error

    def register_all_handlers(self) -> None:
        self.called += 1
        if self.raise_import_error:
            raise ImportError("missing handler module")


class _StubCqrsContainer:
    def __init__(self, registrar: _StubHandlerRegistrar) -> None:
        self.dispatcher_called = 0
        self.registrar = registrar
        self.handler_registrar_called = 0

    def dispatcher(self) -> object:
        self.dispatcher_called += 1
        return object()

    def handler_registrar(self) -> _StubHandlerRegistrar:
        self.handler_registrar_called += 1
        return self.registrar


class _StubProvidersContainer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def storage_provider_type(self) -> str:
        self.calls.append("storage_provider_type")
        return "local"

    def queue_provider_type(self) -> str:
        self.calls.append("queue_provider_type")
        return "rabbitmq"

    def worker_provider_type(self) -> str:
        self.calls.append("worker_provider_type")
        return "docker"

    def llm_provider_type(self) -> str:
        self.calls.append("llm_provider_type")
        return "openai"

    def data_source_provider_type(self) -> str:
        self.calls.append("data_source_provider_type")
        return "edgar"

    def database_provider_type(self) -> str:
        self.calls.append("database_provider_type")
        return "postgres"


class _StubApplicationContainer:
    def __init__(
        self,
        *,
        cqrs_container: _StubCqrsContainer,
        providers_container: _StubProvidersContainer,
    ) -> None:
        self._cqrs_container = cqrs_container
        self._providers_container = providers_container
        self.cqrs_called = 0
        self.providers_container_called = 0

    def cqrs(self) -> _StubCqrsContainer:
        self.cqrs_called += 1
        return self._cqrs_container

    def providers_container(self) -> _StubProvidersContainer:
        self.providers_container_called += 1
        return self._providers_container


class _StubCompositionRootInstance:
    def __init__(self, app_container: _StubApplicationContainer) -> None:
        self._app_container = app_container
        self.wired_modules: list[ModuleType] | None = None

    def wire_modules(self, modules: list[ModuleType]) -> None:
        self.wired_modules = list(modules)

    def get_application_container(self) -> _StubApplicationContainer:
        return self._app_container


@pytest.mark.asyncio
async def test_main_filters_missing_modules_and_registers_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.main as main_module

    monkeypatch.setenv("ENVIRONMENT", "test")

    imported_modules: list[str] = []

    def fake_import_module(module_path: str) -> ModuleType:
        imported_modules.append(module_path)
        return ModuleType(module_path)

    monkeypatch.setattr(main_module, "import_module", fake_import_module)

    existing_files = {
        "src/presentation/api/dependencies.py",
        "src/presentation/api/routers/analyses.py",
    }

    def fake_exists(self: object) -> bool:
        path = str(self).replace("\\", "/")
        return path in existing_files

    monkeypatch.setattr(main_module.Path, "exists", fake_exists, raising=False)

    registrar = _StubHandlerRegistrar()
    cqrs_container = _StubCqrsContainer(registrar)
    providers_container = _StubProvidersContainer()
    app_container = _StubApplicationContainer(
        cqrs_container=cqrs_container,
        providers_container=providers_container,
    )

    root_holder: dict[str, object] = {}

    class StubCompositionRootFactory:
        @staticmethod
        def initialize(environment: str) -> _StubCompositionRootInstance:
            root_holder["environment"] = environment
            root_holder["root"] = _StubCompositionRootInstance(app_container)
            return root_holder["root"]  # type: ignore[return-value]

    monkeypatch.setattr(main_module, "CompositionRoot", StubCompositionRootFactory)

    await main_module.main()

    assert root_holder["environment"] == "test"
    root = root_holder["root"]
    assert isinstance(root, _StubCompositionRootInstance)
    assert root.wired_modules is not None
    assert imported_modules == [
        "src.presentation.api.dependencies",
        "src.presentation.api.routers.analyses",
    ]
    assert [module.__name__ for module in root.wired_modules] == imported_modules

    assert app_container.cqrs_called == 1
    assert cqrs_container.dispatcher_called == 1
    assert cqrs_container.handler_registrar_called == 1
    assert registrar.called == 1

    assert app_container.providers_container_called == 1
    assert providers_container.calls == [
        "storage_provider_type",
        "queue_provider_type",
        "worker_provider_type",
        "llm_provider_type",
        "data_source_provider_type",
        "database_provider_type",
    ]


@pytest.mark.asyncio
async def test_main_skips_wiring_when_no_modules_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.main as main_module

    monkeypatch.delenv("ENVIRONMENT", raising=False)

    def should_not_import(_module_path: str) -> ModuleType:
        raise AssertionError("import_module should not be called")

    monkeypatch.setattr(main_module, "import_module", should_not_import)
    monkeypatch.setattr(main_module.Path, "exists", lambda _self: False, raising=False)

    registrar = _StubHandlerRegistrar()
    cqrs_container = _StubCqrsContainer(registrar)
    providers_container = _StubProvidersContainer()
    app_container = _StubApplicationContainer(
        cqrs_container=cqrs_container,
        providers_container=providers_container,
    )

    root_holder: dict[str, object] = {}

    class StubCompositionRootFactory:
        @staticmethod
        def initialize(environment: str) -> _StubCompositionRootInstance:
            root_holder["environment"] = environment
            root_holder["root"] = _StubCompositionRootInstance(app_container)
            return root_holder["root"]  # type: ignore[return-value]

    monkeypatch.setattr(main_module, "CompositionRoot", StubCompositionRootFactory)

    await main_module.main()

    assert root_holder["environment"] == "development"
    root = root_holder["root"]
    assert isinstance(root, _StubCompositionRootInstance)
    assert root.wired_modules is None


@pytest.mark.asyncio
async def test_main_bubbles_handler_registration_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.main as main_module

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setattr(main_module.Path, "exists", lambda _self: False, raising=False)

    registrar = _StubHandlerRegistrar(raise_import_error=True)
    cqrs_container = _StubCqrsContainer(registrar)
    providers_container = _StubProvidersContainer()
    app_container = _StubApplicationContainer(
        cqrs_container=cqrs_container,
        providers_container=providers_container,
    )

    class StubCompositionRootFactory:
        @staticmethod
        def initialize(_environment: str) -> _StubCompositionRootInstance:
            return _StubCompositionRootInstance(app_container)

    monkeypatch.setattr(main_module, "CompositionRoot", StubCompositionRootFactory)

    with pytest.raises(ImportError, match="missing handler module"):
        await main_module.main()
