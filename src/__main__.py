import argparse
import dotenv

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="path to a config.toml file", default="config.toml")
    parser.add_argument("--env", help="path to a .env file", default=".env")
    args = parser.parse_args()

    dotenv.load_dotenv(args.env, override=True)

    import bureaucrat
    import os

    config = bureaucrat.Config.load(args.config)
    bot = bureaucrat.Bureaucrat(config=config)
    bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
