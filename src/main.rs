mod bureaucrat;
use bureaucrat::{configuration::*, get_routes};

use clap::Parser;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct CLIArgs
{
    #[arg(short, long, default_value = "config.toml")]
    pub config_path: String,
}

#[tokio::main]
async fn main()
{
    // Initialize environment logging.

    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    // Load the Bureaucrat configuration from the specified configuration file.

    let args = CLIArgs::parse();

    Configuration::initialize(&args.config_path).expect("failed to load Bureaucrat configuration");

    let config = Configuration::get();

    log::info!("loaded configuration from {}", &args.config_path);
    log::debug!("configuration: {:?}", &config);

    // Serve the application using TLS.

    let server = warp::serve(get_routes());
    let addr = config
        .server
        .as_addr()
        .parse::<std::net::SocketAddr>()
        .expect("failed to parse server address");

    if config.server.use_tls
    {
        server
            .tls()
            .cert_path(&config.server.tls_pem)
            .key_path(&config.server.tls_key)
            .run(addr)
            .await;
    }
    else
    {
        server.run(addr).await;
    }
}
