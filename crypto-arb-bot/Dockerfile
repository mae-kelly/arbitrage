FROM rust:1.73 as builder

WORKDIR /app
COPY core/Cargo.toml core/Cargo.lock ./
COPY core/src ./src
RUN cargo build --release

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

WORKDIR /app

COPY --from=builder /app/target/release/crypto-arb-bot /app/
COPY package*.json ./
COPY ml ./ml
COPY scripts ./scripts
COPY config ./config
COPY requirements.txt ./

RUN npm install
RUN pip install -r requirements.txt

CMD ["./crypto-arb-bot"]
