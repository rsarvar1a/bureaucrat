mod bureaucrat;
use bureaucrat::{configuration::*, create_client, get_routes};

use anyhow::{Context, Error, Result};
use clap::Parser;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct CLIArgs
{
    #[arg(short, long, default_value = "config.toml")]
    pub config_path: String,
}

#[tokio::main]
async fn main() -> Result<(), Error>
{
    // Load the Bureaucrat configuration from the specified configuration file.

    let args = CLIArgs::parse();

    Configuration::initialize(&args.config_path)
        .context("failed to load Bureaucrat configuration")?;
    let config = Configuration::get();

    // Initialize environment logging.

    if config.debug
    {
        std::env::set_var("RUST_LOG", "debug");
    }
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("warn")).init();

    log::info!("loaded configuration from {}", &args.config_path);
    log::debug!("configuration: {:?}", &config);

    // Subtasks for each part of Bureaucrat (webserver and Discord client).

    let (d, s) = tokio::join!(tokio::spawn(discord_main()), tokio::spawn(server_main()));

    if let Some(e) = d.err()
    {
        log::error!("failed to run Discord client: {}", e);
    }
    if let Some(e) = s.err()
    {
        log::error!("failed to run webserver: {}", e);
    }

    Ok(())
}

async fn discord_main() -> Result<(), Error>
{
    // Instantiate the client and run it.

    let mut client = create_client()
        .await
        .context("failed to construct client")?;

    client.start().await.context("fatal error in client")?;

    Ok(())
}

async fn server_main() -> Result<(), Error>
{
    let config = Configuration::get();

    // Serve the application using TLS.

    let routes = get_routes().context("failed to build routes")?;

    let server = warp::serve(routes);
    let addr = config
        .server
        .as_addr()
        .parse::<std::net::SocketAddr>()
        .context("failed to parse server address")?;

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

    Ok(())
}
