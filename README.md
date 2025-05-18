# SwarmScrape
***Work in progress***

A pseudo proxy server built for simple web scraping.
Using the nodriver python library,
this server sets up a pool of agents that pull websites requested by clients,
removes scripts, styling, and images,
and returns the raw html to the client.

Along with an API key in the header (in the `X-API-Key' field),
add the desired url in the `url` url parameter.
Like this:
```
http://<server>/?url=<website>
```

## To-do
- Make API keys configuration option (required by default currently)
- Implement randomized user-agents for each member of the pool
- Make python client library

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](./LICENSE.md) file for details.
