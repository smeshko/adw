#!/bin/bash
# A hook script that outputs environment variables
echo "ADW_RUN_ID=$ADW_RUN_ID"
echo "ADW_PHASE=$ADW_PHASE"
echo "ADW_FEATURE=$ADW_FEATURE"
echo "ADW_ARTIFACTS_DIR=${ADW_ARTIFACTS_DIR:-not_set}"
echo "ADW_CONTEXT_FILE=${ADW_CONTEXT_FILE:-not_set}"
exit 0
