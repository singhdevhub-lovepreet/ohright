import { Action, ActionPanel, Detail, Icon, List, open, showToast, Toast } from "@raycast/api";
import { useState, useEffect } from "react";
import { checkSetup } from "./shared";

export default function SetupCommand() {
  const [setup, setSetup] = useState<ReturnType<typeof checkSetup> | null>(null);

  useEffect(() => {
    setSetup(checkSetup());
  }, []);

  const recheck = () => setSetup(checkSetup());

  if (!setup) return <List isLoading />;

  return (
    <List>
      <List.Section title="OhRight Setup Status">
        <List.Item
          icon={setup.installed ? Icon.CheckCircle : Icon.XMarkCircle}
          title="OhRight CLI installed"
          subtitle={setup.installed ? "~/.ohright/" : "Not installed"}
          accessories={[{ text: setup.installed ? "✅" : "❌" }]}
          actions={
            !setup.installed ? (
              <ActionPanel>
                <Action.OpenInBrowser
                  title="Install Guide"
                  url="https://github.com/singhdevhub-lovepreet/ohright#setup"
                />
              </ActionPanel>
            ) : undefined
          }
        />
        <List.Item
          icon={setup.hasKeys ? Icon.CheckCircle : Icon.XMarkCircle}
          title="API keys configured"
          subtitle={setup.hasKeys ? "OpenAI + screenpipe keys set" : "Missing keys"}
          accessories={[{ text: setup.hasKeys ? "✅" : "❌" }]}
          actions={
            !setup.hasKeys && setup.installed ? (
              <ActionPanel>
                <Action title="Add OpenAI Key" onAction={() => open("terminal: echo 'sk-your-key' > ~/.ohright/.openai_key")} />
                <Action.OpenInBrowser title="Get OpenAI Key" url="https://platform.openai.com/api-keys" />
              </ActionPanel>
            ) : undefined
          }
        />
        <List.Item
          icon={setup.screenpipeRunning ? Icon.CheckCircle : Icon.XMarkCircle}
          title="screenpipe running"
          subtitle={setup.screenpipeRunning ? "localhost:3030" : "Not running"}
          accessories={[{ text: setup.screenpipeRunning ? "✅" : "❌" }]}
          actions={
            !setup.screenpipeRunning ? (
              <ActionPanel>
                <Action
                  title="Start screenpipe"
                  onAction={() => open("terminal: npx screenpipe@latest record")}
                />
                <Action.OpenInBrowser title="screenpipe Docs" url="https://docs.screenpi.pe" />
              </ActionPanel>
            ) : undefined
          }
        />
      </List.Section>

      <List.Section title="Quick Actions">
        <List.Item
          icon={Icon.Download}
          title="Refresh Status"
          subtitle="Re-check all components"
          actions={<ActionPanel><Action title="Refresh" onAction={recheck} /></ActionPanel>}
        />
        <List.Item
          icon={Icon.Book}
          title="View Documentation"
          subtitle="Setup guide and API reference"
          actions={
            <ActionPanel>
              <Action.OpenInBrowser title="Open Docs" url="https://github.com/singhdevhub-lovepreet/ohright" />
            </ActionPanel>
          }
        />
      </List.Section>
    </List>
  );
}
