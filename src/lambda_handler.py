"""AWS Lambda entrypoint.

Mangum adapts the ASGI app to a Lambda Function URL event. One function, one
URL, no API Gateway and no VPC — the simplest AWS surface that can serve this.
"""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
