import { Action, ActionPanel, Form, Icon, List, showToast, Toast } from "@raycast/api";
import { useState, useEffect } from "react";
import { OhRightResult, OhRightStats, runQuery, runAsk, attentionBar, typeEmoji, checkSetup } from "./shared";

export default function AskCommand() {
  const [searchText, setSearchText] = useState("");
  const [results, setResults] = useState<OhRightResult[]>([]);
  const [stats, setStats] = useState<OhRightStats | null>(null);
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const executeQuery = async (query: string) => {
    if (!query.trim()) {
      // Default: show obsessions
      setIsLoading(true);
      const data = runQuery("obsessions");
      setIsLoading(false);
      if (Array.isArray(data)) {
        setResults(data);
        setStats(null);
        setMessage("Your current obsessions:");
      }
      return;
    }

    setIsLoading(true);

    // Quick keyword detection (same as fallback in ask.py for speed)
    const q = query.toLowerCase();
    let command = "search";
    let arg = query;

    if (q.match(/obsess|interest|song|music|listen/)) {
      command = "obsessions";
      arg = "";
      setMessage("Your most played:");
    } else if (q.match(/product|buy|shopping|purchas|forgot/)) {
      command = "products";
      arg = "";
      setMessage("Products you researched:");
    } else if (q.match(/abandon|drop|unfinished|stopped/)) {
      command = "abandoned";
      arg = "";
      setMessage("Things you dropped:");
    } else if (q.match(/stat|graph|summary|overview/)) {
      const data = runQuery("stats");
      setIsLoading(false);
      if (!Array.isArray(data)) {
        setStats(data as OhRightStats);
        setResults([]);
        setMessage("Your behavioral graph:");
      }
      return;
    }

    const data = runQuery(command, arg);
    setIsLoading(false);

    if (Array.isArray(data)) {
      setResults(data);
      setStats(null);
    } else {
      setStats(data as OhRightStats);
      setResults([]);
    }
  };

  // Run on mount
  useEffect(() => {
    executeQuery("");
  }, []);

  return (
    <List
      isLoading={isLoading}
      searchText={searchText}
      onSearchTextChange={(text) => {
        setSearchText(text);
        if (text.length === 0 || text.length > 2) {
          executeQuery(text);
        }
      }}
      searchBarPlaceholder="Ask about your digital life — songs, products, obsessions..."
      throttle
    >
      {message && (
        <List.Section title={message}>
          {results.map((item, i) => (
            <List.Item
              key={i}
              icon={typeEmoji(item.type)}
              title={item.title}
              subtitle={item.subtitle}
              accessories={[
                { text: attentionBar(item.attention || item.match || 0) },
              ]}
              actions={
                <ActionPanel>
                  {item.url && (
                    <Action.OpenInBrowser
                      title="Open in Browser"
                      url={item.url}
                      icon={Icon.Globe}
                    />
                  )}
                  <Action.CopyToClipboard
                    title="Copy Title"
                    content={item.title}
                  />
                  {item.url && (
                    <Action.CopyToClipboard
                      title="Copy URL"
                      content={item.url}
                      icon={Icon.Link}
                    />
                  )}
                </ActionPanel>
              }
              detail={
                <List.Item.Detail
                  metadata={
                    <List.Item.Detail.Metadata>
                      <List.Item.Detail.Metadata.Label
                        title="Type"
                        text={item.type}
                      />
                      <List.Item.Detail.Metadata.Label
                        title="Attention"
                        text={`${((item.attention || 0) * 100).toFixed(0)}%`}
                      />
                      {item.revisits !== undefined && (
                        <List.Item.Detail.Metadata.Label
                          title="Revisits"
                          text={String(item.revisits)}
                        />
                      )}
                      {item.last_seen && (
                        <List.Item.Detail.Metadata.Label
                          title="Last Seen"
                          text={item.last_seen}
                        />
                      )}
                      {item.url && (
                        <List.Item.Detail.Metadata.Link
                          title="Source URL"
                          target={item.url}
                          text={item.url.length > 60 ? item.url.slice(0, 60) + "..." : item.url}
                        />
                      )}
                    </List.Item.Detail.Metadata>
                  }
                />
              }
            />
          ))}
        </List.Section>
      )}

      {stats && (
        <List.Section title={message}>
          <List.Item
            icon={Icon.BarChart}
            title={`${stats.graph.total_nodes} topics tracked`}
            subtitle={`${stats.graph.active} active · ${stats.graph.abandoned} abandoned`}
            accessories={[{ text: `${stats.events.semantic} semantic events` }]}
          />
          {Object.entries(stats.types).map(([type, count]) => (
            <List.Item
              key={type}
              icon={typeEmoji(type)}
              title={type}
              subtitle={`${count} items`}
            />
          ))}
        </List.Section>
      )}

      {!isLoading && results.length === 0 && !stats && searchText && (
        <List.EmptyView
          icon={Icon.MagnifyingGlass}
          title="Nothing found"
          description="Browse more and OhRight will learn your patterns."
        />
      )}

      {!isLoading && results.length === 0 && !stats && !searchText && (
        <List.EmptyView
          icon={Icon.QuestionMark}
          title="OhRight is ready"
          description="Type a query like 'songs I listened to' or 'products I researched'"
        />
      )}
    </List>
  );
}
