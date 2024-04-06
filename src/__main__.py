import dotenv

dotenv.load_dotenv(".env", override=True)

import bureaucrat
import os


def main():

    config = bureaucrat.Config.load("config.toml")
    bot = bureaucrat.Bureaucrat(config=config)
    bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
