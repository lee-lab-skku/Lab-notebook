# Research Scripts

This repository contains the `scripts/` portion of my research workflow.

## Overview

The scripts are mainly used for:

- collecting papers and metadata from Zotero
- extracting and cleaning PDF text
- analyzing references and claims with LLM-based pipelines
- running small utility checks for the local research environment

## Structure

- `scripts/`: main research and utility scripts
- `scripts/archive/`: older pipeline versions kept for reference
- `scripts/utils/`: helper and test scripts

## Notes

- Some scripts assume a local environment such as Zotero API access, local file paths, or an Ollama/OpenAI-compatible endpoint.
- Before reuse, check environment variables, API keys, and path settings in each script.
