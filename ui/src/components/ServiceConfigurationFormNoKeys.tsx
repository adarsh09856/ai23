"use client";

import { Save } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";

export type ServiceSegment = "llm" | "tts" | "stt" | "embeddings" | "realtime";

export interface ProviderSchema {
    title?: string;
    description?: string;
    properties: Record<string, any>;
    required?: string[];
}

export interface ServiceConfigurationDefaults {
    llm: Record<string, ProviderSchema>;
    tts: Record<string, ProviderSchema>;
    stt: Record<string, ProviderSchema>;
    embeddings: Record<string, ProviderSchema>;
    realtime?: Record<string, ProviderSchema>;
    default_providers: Partial<Record<ServiceSegment, string>>;
}

interface ServiceConfigurationFormNoKeysProps {
    mode: 'global' | 'override';
    forceRealtime?: boolean;
    configurationDefaults: ServiceConfigurationDefaults;
    initialConfig: Record<string, any>;
    submitLabel?: string;
    onSave: (config: any) => Promise<void>;
}

const PIPELINE_TABS: { key: ServiceSegment; label: string }[] = [
    { key: "llm", label: "LLM" },
    { key: "tts", label: "Voice" },
    { key: "stt", label: "Transcriber" },
    { key: "embeddings", label: "Embedding" },
];

const REALTIME_TABS: { key: ServiceSegment; label: string }[] = [
    { key: "realtime", label: "Realtime Model" },
    { key: "llm", label: "LLM" },
    { key: "embeddings", label: "Embedding" },
];

// Common providers and their popular models
const COMMON_MODELS: Record<string, Record<string, string[]>> = {
    openai: {
        llm: ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        tts: ["tts-1", "tts-1-hd"],
        stt: ["whisper-1"],
        embeddings: ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"],
        realtime: ["gpt-4o-realtime-preview"]
    },
    anthropic: {
        llm: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
    },
    google: {
        llm: ["gemini-1.5-pro", "gemini-1.5-flash"],
        tts: ["en-US-Casual", "en-US-Standard-A"],
        stt: ["default"]
    },
    azure: {
        llm: ["gpt-4", "gpt-35-turbo"],
        tts: ["en-US-AriaNeural", "en-US-JennyNeural"],
        stt: ["en-US"]
    },
    elevenlabs: {
        tts: ["eleven_monolingual_v1", "eleven_multilingual_v2"]
    }
};

function ServiceConfigRow({ 
    service, 
    label, 
    value, 
    onChange, 
    providers 
}: {
    service: ServiceSegment;
    label: string;
    value: any;
    onChange: (value: any) => void;
    providers: Record<string, ProviderSchema>;
}) {
    const [selectedProvider, setSelectedProvider] = useState(value?.provider || "");
    const [selectedModel, setSelectedModel] = useState(value?.model || "");

    const handleProviderChange = (provider: string) => {
        setSelectedProvider(provider);
        setSelectedModel(""); // Reset model when provider changes
        onChange({
            ...value,
            provider,
            model: ""
        });
    };

    const handleModelChange = (model: string) => {
        setSelectedModel(model);
        onChange({
            ...value,
            model
        });
    };

    const availableModels = COMMON_MODELS[selectedProvider]?.[service] || [];

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    {label}
                    <Badge variant="outline">Admin Keys</Badge>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div>
                    <Label>Provider</Label>
                    <Select value={selectedProvider} onValueChange={handleProviderChange}>
                        <SelectTrigger>
                            <SelectValue placeholder="Select provider" />
                        </SelectTrigger>
                        <SelectContent>
                            {Object.entries(providers).map(([providerId, schema]) => (
                                <SelectItem key={providerId} value={providerId}>
                                    {schema.title || providerId}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {selectedProvider && (
                    <div>
                        <Label>Model</Label>
                        <Select value={selectedModel} onValueChange={handleModelChange}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select model" />
                            </SelectTrigger>
                            <SelectContent>
                                {availableModels.map((model) => (
                                    <SelectItem key={model} value={model}>
                                        {model}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {availableModels.length === 0 && (
                            <p className="text-sm text-muted-foreground mt-1">
                                Enter custom model name if needed
                            </p>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

export function ServiceConfigurationFormNoKeys({
    mode,
    forceRealtime = false,
    configurationDefaults,
    initialConfig,
    submitLabel = "Save Configuration",
    onSave
}: ServiceConfigurationFormNoKeysProps) {
    const [isRealtime, setIsRealtime] = useState(forceRealtime || initialConfig.mode === "realtime");
    const [config, setConfig] = useState(initialConfig);
    const [isSaving, setIsSaving] = useState(false);

    const tabs = isRealtime ? REALTIME_TABS : PIPELINE_TABS;

    const updateServiceConfig = (service: ServiceSegment, serviceConfig: any) => {
        const newConfig = {
            ...config,
            [service]: serviceConfig
        };
        
        // Update mode based on realtime selection
        if (isRealtime) {
            newConfig.mode = "realtime";
            newConfig.realtime = newConfig.realtime || {};
        } else {
            newConfig.mode = "pipeline";
            newConfig.pipeline = newConfig.pipeline || {};
        }
        
        setConfig(newConfig);
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await onSave(config);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="space-y-6">
            {!forceRealtime && (
                <div className="flex items-center space-x-2">
                    <Label htmlFor="realtime-toggle">Realtime Mode</Label>
                    <input
                        id="realtime-toggle"
                        type="checkbox"
                        checked={isRealtime}
                        onChange={(e) => setIsRealtime(e.target.checked)}
                        className="rounded"
                    />
                    <span className="text-sm text-muted-foreground">
                        Use single realtime model for conversation
                    </span>
                </div>
            )}

            <Tabs defaultValue={tabs[0].key}>
                <TabsList>
                    {tabs.map((tab) => (
                        <TabsTrigger key={tab.key} value={tab.key}>
                            {tab.label}
                        </TabsTrigger>
                    ))}
                </TabsList>

                {tabs.map((tab) => (
                    <TabsContent key={tab.key} value={tab.key}>
                        <ServiceConfigRow
                            service={tab.key}
                            label={tab.label}
                            value={config[tab.key] || {}}
                            onChange={(value) => updateServiceConfig(tab.key, value)}
                            providers={isRealtime && tab.key === "realtime" 
                                ? configurationDefaults.realtime || {}
                                : configurationDefaults[tab.key]}
                        />
                    </TabsContent>
                ))}
            </Tabs>

            <Button 
                onClick={handleSave} 
                disabled={isSaving}
                className="w-full"
            >
                <Save className="mr-2 h-4 w-4" />
                {isSaving ? "Saving..." : submitLabel}
            </Button>
        </div>
    );
}
