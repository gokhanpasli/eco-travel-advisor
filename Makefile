.PHONY: install train validate run-actions run-rasa run-ui evaluate docker-train docker-up

install:
	pip install -r requirements.txt
	pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.4.1/en_core_web_md-3.4.1-py3-none-any.whl

validate:
	rasa data validate

train: validate
	rasa train

run-actions:
	rasa run actions --port 5055

run-rasa:
	rasa run --enable-api --cors "*" --endpoints endpoints.yml --port 5005

run-ui:
	streamlit run ui/app.py --server.port 8501

evaluate:
	bash scripts/evaluate.sh

docker-train:
	docker compose run --rm rasa train

docker-up:
	docker compose up --build
