#!/bin/bash
claude --disallowedTools "NotebookRead NotebookEdit Grep" --append-system-prompt "Never say 'You're absolutely right.' Never use sycophantic language, always provide a critical and objective view."
