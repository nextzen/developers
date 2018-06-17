# API Key Check

This is a small bit of Node code that sits in [Lambda@Edge](https://docs.aws.amazon.com/lambda/latest/dg/lambda-edge.html) and checks an API key before allowing a CloudFront request through.

## Deploy

1. Run `npm install` from this directory to pull down the dependencies.

1. Zip up the code and dependencies using `zip CheckApiKeyAtEdge.zip -r index.js node_modules`.

1. Upload the resulting zipfile to the AWS [Lambda Console(https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions). Note that you might need to create the functions in us-east-1/Virginia.

1. In the "Designer" section for the Lambda function, select "CloudFront" as the trigger, pick the distribution, and select the origins you want to trigger on. This function is designed to use the "Origin Request" trigger.
