FROM rust:latest AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY Cargo.toml ./
RUN touch Cargo.lock
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

COPY src ./src
RUN touch src/main.rs
RUN cargo build --release

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    torch==2.1.0 \
    numpy==1.24.3 \
    scipy==1.11.4 \
    pandas==2.1.3 \
    scikit-learn==1.3.2

WORKDIR /app

COPY --from=builder /app/target/release/quantum-arb /app/quantum-arb
COPY ml ./ml

RUN mkdir -p /app/logs /app/data

ENV RUST_LOG=info
ENV PYTHONPATH=/app

CMD ["./quantum-arb"]