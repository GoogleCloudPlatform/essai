# Concepts and architecture

EssAI is an experiment that leverages Google AI platform (especifically, [Gemini](https://blog.google/technology/ai/google-gemini-ai/)) in Google Cloud to automate the process of automatically correcting essays, saving time for teachers and allowing big institutions to scale this task-intense and repetitive process.

It was designed to be used as an **assistent to educators** in the task of correcting essays, which is very time consuming by nature. It does not intend to replace teachers and/or tutors, rather, its main goal is to allow theses professionals to focus their attention and very deep set of skills into the process of teaching-learning itself that should not be done solely by AI.

## Model customization

This version of the experiment runs on top of Gemini 1.5 Pro, which is then customized to "respect" specific rubrics (in the case of this demo, [Brazilian rubrics for a national test known as ENEM](https://download.inep.gov.br/publicacoes/institucionais/avaliacoes_e_exames_da_educacao_basica/a_redacao_no_enem_2024_cartilha_do_participante.pdf) applied in the country for essay correction).

Despite the fact that this version is configured to correct essays against Brazilian rubrics only, it is our intention to bring other rubrics over time.

You could also create your own customization (in terms of rubrics to be considered) and then, adjust this application to call your updated correction model APIs. For more details, see the doc [accessing APIs](/docs/accessing-api.md).

## Functional and Non-Functional Architectures

EssAI is a very lightweight application that follows the traditional three-layer web application model: web frontend, wrapper API (REST), and databases, as illustrated by the image below.

![Essay App Layers](/img/essai-app-layers.png)

Under-the-hood, the application was written in Python and relies in a relational database for persisting its data (Postgres).

On the "non-functional" side, there is a lot more going on with various components being deployed together to support the automation of the correction process, as you can see below. For details about the deployment process, please visit [this document](/docs/deploying-essai.md).

![Non-functional architecture for EssAI](/img/essai-architecture-english.png)

The general automation flow is described below:

* Essay is produced by the student and is then sent for evaluation through the web interface (it can be in or out GCP - this demo relies on [Streamlit](https://streamlit.io/)). In the case of this demo, those essays are pre-populated, in pt-BR and are fake generated texts.

* Once an essay is sent for correction it is automatically picked up by the Correction API (also known as correction producer) and queued up in [PubSub](https://cloud.google.com/pubsub?hl=en).

* A consumer function (known as Consumer EssAI) dequeues the message from the queue and send it for correction with Gemini. Results are also consolidated in the database ([Cloud SQL for Postgres](https://cloud.google.com/sql). 

* Once ready (corrected), the "Correction API (return)" picks up the correction in the database, formats its return and then send it back to be visualized by users in the frontend. 

* Static files are saved in a [GCS bucket](https://cloud.google.com/storage?hl=en) while, for scenarios where analytical analysis is needed, [Data Sync](https://cloud.google.com/vertex-ai/docs/featurestore/latest/sync-data) works with [BigQuery](https://cloud.google.com/bigquery?hl=en) to make that happen.

* APIs and Functions are deployed as [Cloud Run](https://cloud.google.com/run?hl=en) resources in Google Cloud. A [Cloud Load Balancer](https://cloud.google.com/load-balancing?hl=en) also gets deployed in front of the infrastructue alongside [Cloud Armor (WAF)](https://cloud.google.com/security/products/armor?hl=en) for protection of malformed incoming requests.