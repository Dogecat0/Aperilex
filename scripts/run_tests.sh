#!/bin/bash
TEST_PATH=${1:-tests/}
poetry run pytest "$TEST_PATH"
