FROM python:3.12-slim

WORKDIR /workspace

# Dependencies are stdlib-only so the image builds offline after the base
# image is available. No network needed at agent/eval time.
COPY source/ /tmp/source-template/

CMD ["bash"]
