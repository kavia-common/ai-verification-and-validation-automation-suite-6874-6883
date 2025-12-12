#!/bin/bash
cd /home/kavia/workspace/code-generation/ai-verification-and-validation-automation-suite-6874-6883/vv_backend_api
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

