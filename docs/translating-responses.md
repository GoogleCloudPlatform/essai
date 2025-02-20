# Translating model responses to your language

By default, EssAI's translations come out in Brazilian portuguese. However, you can get off the answer to whatever language you would like to test this for.

This document describes the steps you need to perform in order to change correction idiom.

## Update the langague instruction

Language change afftect two main files, described below.

* `template-correcao-enem.yml.j2`
* `template-sumarizacao-enem.yml.j2`

Please, notice that these files are located in the "Prompts" directory.

For instance: if you want EssAI's correction result to come out in English, in the file `template-sumarizacao-enem.yml.j2` you must uncomment the line which says "Dê todos os resultados em inglês.".

You also need to uncomment the line 298 in the file `template-correcao-enem.yml.j2`, which says "Dê todos os resultados em inglês.".

If you want EssAI to send off the results in whatever other language (Spanish, for instance), you must change that sentence on both files.

For instance: if you the correction in Spanish, the sentence must be updated to "Dê todos os resultados em **espanhol**".

By doing so you will be altering the prompt sent to Gemini and instructing it to now send correction's result in Spanish (or whatever language that applies to you).