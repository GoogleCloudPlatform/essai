# Accessing the API

If you followed the steps described in [this doc](/docs/deploying-essai.md), at this point you should have EssAI deployed in your Google Cloud environment.

As a first step, you might consider understanding better the API that performs the various correction steps under-the-hood. If that's something you are considering, then this document is for your.

# Where is my API deployed?

As described by the [concepts and architecture document](/docs/concepts-architecture.md), both frontend web application and backend API runs on top of the Cloud Run service.

Considering that the API implements the pattern defined by [Open API](https://www.openapis.org/), from your Google Cloud console, if you go to the Cloud Run service page you're going to be able to see three different resources deployed there, as depicted below.

![EssAI's resources deployed in Cloud Run](/img/essai-cloud-run-resources.png)

Don't get attached to resources names. They might differ depending on the values provided on the step 4 of the [deployment document](/docs/deploying-essai.md).

In the case of the example shown by the picture above, the API sits on the `essai-cloud-run` resource. To see the API running, just go ahead and click on the resource name, grab the URL for the resource, append the word 'docs' at the end of the URL and then, run it in your browser.

The address formated to directly access the API should look like the below.

```
https://{your-cloud-run-fqdn}.{your-region-selected}.run.app/docs
```

At the end of this process, you should be seen a screen like the one presented by the image below as result.

![Open API definition for EssAI's API](/img/essai-api-openapi.png)

# Explore API's endpoints

Make sure to explore every endpoint and method to understand how the API works. It will be particularly useful if you're looking to develop and different frontend for the application moving forward.