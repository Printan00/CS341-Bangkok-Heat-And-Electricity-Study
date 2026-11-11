import sys
from pathlib import Path

# The validate Lambda is deployed as the flat folder lambdas/validate/ (see infra/terraform/lambda.tf),
# so its modules are imported the same way here.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lambdas" / "validate"))
