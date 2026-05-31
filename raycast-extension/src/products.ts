import { Action, ActionPanel, Icon, List } from "@raycast/api";
import { useState, useEffect } from "react";
import { OhRightResult, runQuery, attentionBar, typeEmoji } from "./shared";

export default function ProductsCommand() {
  const [results, setResults] = useState<OhRightResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const data = runQuery("products");
    if (Array.isArray(data)) {
      setResults(data);
    }
    setIsLoading(false);
  }, []);

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Filter products...">
      <List.Section title="Products You're Researching">
        {results.map((item, i) => (
          <List.Item
            key={i}
            icon={typeEmoji(item.type)}
            title={item.title}
            subtitle={item.subtitle}
            accessories={[{ text: attentionBar(item.attention) }]}
            actions={
              <ActionPanel>
                {item.url && <Action.OpenInBrowser title="Open Product Page" url={item.url} icon={Icon.Globe} />}
                <Action.CopyToClipboard title="Copy Product Name" content={item.title} />
                {item.url && <Action.CopyToClipboard title="Copy URL" content={item.url} />}
              </ActionPanel>
            }
          />
        ))}
      </List.Section>

      {!isLoading && results.length === 0 && (
        <List.EmptyView
          icon={Icon.Cart}
          title="No product research yet"
          description="Browse Amazon or Flipkart — OhRight tracks product pages."
        />
      )}
    </List>
  );
}
