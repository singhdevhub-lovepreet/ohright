import { Action, ActionPanel, Icon, List } from "@raycast/api";
import { useState, useEffect } from "react";
import { OhRightResult, runQuery, attentionBar, typeEmoji } from "./shared";

export default function ObsessionsCommand() {
  const [results, setResults] = useState<OhRightResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const data = runQuery("obsessions");
    if (Array.isArray(data)) {
      setResults(data);
    }
    setIsLoading(false);
  }, []);

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Filter obsessions...">
      <List.Section title="Your Current Obsessions">
        {results.map((item, i) => (
          <List.Item
            key={i}
            icon={typeEmoji(item.type)}
            title={item.title}
            subtitle={item.subtitle}
            accessories={[{ text: attentionBar(item.attention) }]}
            actions={
              <ActionPanel>
                {item.url && <Action.OpenInBrowser title="Open in Browser" url={item.url} icon={Icon.Globe} />}
                <Action.CopyToClipboard title="Copy Title" content={item.title} />
                {item.url && <Action.CopyToClipboard title="Copy URL" content={item.url} />}
              </ActionPanel>
            }
          />
        ))}
      </List.Section>

      {!isLoading && results.length === 0 && (
        <List.EmptyView
          icon={Icon.Heart}
          title="No obsessions yet"
          description="Keep browsing — OhRight learns from your activity."
        />
      )}
    </List>
  );
}
