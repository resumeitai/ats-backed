#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Download spaCy English model for ATS analysis
python -m spacy download en_core_web_lg

# Download NLTK data for synonym expansion
python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4'); nltk.download('averaged_perceptron_tagger'); nltk.download('punkt')"

python manage.py migrate
python manage.py collectstatic --no-input
