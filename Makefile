all:
	flux start flux-restful serve --host=0.0.0.0 --port=5000 --workers=2

# Create the tables and the FLUX_USER / FLUX_TOKEN superuser
init:
	flux-restful init
