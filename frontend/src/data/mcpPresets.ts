export interface MCPPreset {
  name: string;
  description: string;
  endpoint: string;
  protocol: 'rest' | 'sse';
  auth_type: 'none' | 'api_key' | 'bearer';
  auth_placeholder?: string; // label shown in the key input
  capabilities: string[];
}

export const MCP_PRESETS: MCPPreset[] = [
  {
    name: 'Brave Search',
    description: 'Web search powered by Brave — privacy-focused, no tracking.',
    endpoint: 'https://api.search.brave.com/mcp',
    protocol: 'sse',
    auth_type: 'api_key',
    auth_placeholder: 'Brave Search API Key',
    capabilities: ['web_search', 'news_search'],
  },
  {
    name: 'Firecrawl',
    description: 'Web crawling and content extraction — scrape any page into clean markdown.',
    endpoint: 'https://mcp.firecrawl.dev',
    protocol: 'sse',
    auth_type: 'bearer',
    auth_placeholder: 'Firecrawl API Key',
    capabilities: ['web_scraping', 'crawling'],
  },
  {
    name: 'GitHub',
    description: 'Search repositories, read files, list issues and PRs.',
    endpoint: 'https://api.githubcopilot.com/mcp',
    protocol: 'sse',
    auth_type: 'bearer',
    auth_placeholder: 'GitHub Personal Access Token',
    capabilities: ['code_search', 'repositories'],
  },
  {
    name: 'Filesystem (local)',
    description: 'Read files from a local directory via a locally-running MCP server.',
    endpoint: 'http://localhost:3100',
    protocol: 'sse',
    auth_type: 'none',
    capabilities: ['file_read', 'directory_listing'],
  },
];
