build:
    (cd client && npm run build)
    cargo build --release

dev:
    (RUST_LOG=debug cargo run) &
    cd client 
    npm run dev

run:
    ./target/release/bureaucrat

go:
    just build
    just run

count:
    cloc src client/src
