FROM        python:3.5

WORKDIR     /app
RUN         pip install pipenv
ADD         Pipfile* /tmp/
RUN         cd /tmp && pipenv install --skip-lock --system --deploy

ADD         ./hsdexplorer/ /app/
RUN	    	COLLECTSTATIC=1 python manage.py collectstatic; unset COLLECTSTATIC

ENTRYPOINT  ["gunicorn", "--bind", "0.0.0.0:8000", "--log-level", "debug", "hsdexplorer.wsgi"]
