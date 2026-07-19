#!/usr/bin/env bash
# Runs the full evaluation suite against the latest trained model:
#   1. Held-out NLU test set
#   2. Five-fold NLU cross-validation
#   3. Rasa Core test stories
#   4. Blind NLU test set (written after training, never seen by the model)
set -euo pipefail

LATEST_MODEL=$(ls -t models/*.tar.gz 2>/dev/null | head -n 1 || true)

if [ -z "${LATEST_MODEL}" ]; then
    echo "No trained model found in models/. Run 'make train' first."
    exit 1
fi

echo "Evaluating model: ${LATEST_MODEL}"
export MPLBACKEND=Agg

echo ""
echo "=== 1/4 Held-out NLU evaluation ==="
rm -rf results/nlu_heldout
rasa test nlu \
    --model "${LATEST_MODEL}" \
    --nlu tests/test_nlu.yml \
    --out results/nlu_heldout

echo ""
echo "=== 2/4 Five-fold NLU cross-validation ==="
rm -rf results/nlu_cross_validation
rasa test nlu \
    --nlu data/nlu.yml \
    --cross-validation \
    --folds 5 \
    --out results/nlu_cross_validation

echo ""
echo "=== 3/4 Core test stories ==="
rm -rf results/core_test
rasa test core \
    --model "${LATEST_MODEL}" \
    --stories tests/test_stories.yml \
    --out results/core_test

echo ""
echo "=== 4/4 Blind NLU evaluation ==="
rm -rf results/final_blind_nlu_test
rasa test nlu \
    --model "${LATEST_MODEL}" \
    --nlu tests/final_test_nlu.yml \
    --out results/final_blind_nlu_test

echo ""
echo "All evaluations completed. Reports are in results/."
