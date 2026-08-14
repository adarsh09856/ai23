"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Trash2, Save, Plus, Eye, EyeOff, TestTube, CheckCircle, AlertCircle } from "lucide-react";
import { toast } from "sonner";

interface ProviderKey {
  api_key: string | string[];
  enabled: boolean;
  api_key_count?: number;
  extra?: Record<string, any>;
}

interface ProviderPolicy {
  enabled_models: string[];
  default_model?: string;
  hidden: boolean;
  premium_only: boolean;
}

interface ProviderCatalogEntry {
  id: string;
  name: string;
  models: string[];
  has_key: boolean;
  enabled: boolean;
  api_key_count: number;
  policy?: ProviderPolicy;
}

interface ProviderCatalogResponse {
  llm: ProviderCatalogEntry[];
  tts: ProviderCatalogEntry[];
  stt: ProviderCatalogEntry[];
  embeddings: ProviderCatalogEntry[];
  realtime: ProviderCatalogEntry[];
}

const SERVICE_TABS = [
  { id: "llm", label: "LLM", description: "Large Language Models" },
  { id: "tts", label: "TTS", description: "Text-to-Speech" },
  { id: "stt", label: "STT", description: "Speech-to-Text" },
  { id: "embeddings", label: "Embeddings", description: "Vector Embeddings" },
  { id: "realtime", label: "Realtime", description: "Real-time Models" },
];

export default function ProvidersPage() {
  const [activeTab, setActiveTab] = useState("llm");
  const [catalog, setCatalog] = useState<ProviderCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});

  useEffect(() => {
    loadProviderCatalog();
  }, []);

  const loadProviderCatalog = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/admin/providers/catalog", {
        credentials: "include"
      });

      if (response.ok) {
        const data = await response.json();
        setCatalog(data);
      } else {
        toast.error("Failed to load provider catalog");
      }
    } catch (error) {
      console.error("Failed to load provider catalog:", error);
      toast.error("Failed to load provider catalog");
    } finally {
      setLoading(false);
    }
  };

  const saveProviderKey = async (providerId: string, keyData: any) => {
    try {
      setSaving(providerId);
      
      const response = await fetch(`/api/admin/providers/${providerId}/key`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(keyData)
      });

      if (response.ok) {
        toast.success(`${providerId.toUpperCase()} key saved successfully`);
        await loadProviderCatalog(); // Reload to get updated status
        setKeyInputs(prev => ({ ...prev, [providerId]: "" })); // Clear input
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to save provider key");
      }
    } catch (error) {
      console.error("Failed to save provider key:", error);
      toast.error("Failed to save provider key");
    } finally {
      setSaving(null);
    }
  };

  const deleteProviderKey = async (providerId: string) => {
    if (!confirm(`Are you sure you want to delete the API key for ${providerId}? This will affect all users using this provider.`)) {
      return;
    }

    try {
      setSaving(providerId);
      
      const response = await fetch(`/api/admin/providers/${providerId}/key`, {
        method: "DELETE",
        credentials: "include"
      });

      if (response.ok) {
        toast.success(`${providerId.toUpperCase()} key deleted successfully`);
        await loadProviderCatalog();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to delete provider key");
      }
    } catch (error) {
      console.error("Failed to delete provider key:", error);
      toast.error("Failed to delete provider key");
    } finally {
      setSaving(null);
    }
  };

  const toggleProvider = async (providerId: string, enabled: boolean) => {
    try {
      setSaving(providerId);
      
      const response = await fetch(`/api/admin/providers/${providerId}/toggle?enabled=${enabled}`, {
        method: "PATCH",
        credentials: "include"
      });

      if (response.ok) {
        toast.success(`Provider ${enabled ? 'enabled' : 'disabled'} successfully`);
        await loadProviderCatalog();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to update provider status");
      }
    } catch (error) {
      console.error("Failed to toggle provider:", error);
      toast.error("Failed to update provider");
    } finally {
      setSaving(null);
    }
  };

  const ProviderCard = ({ provider, serviceType }: { provider: ProviderCatalogEntry; serviceType: string }) => {
    const inputKey = `${serviceType}-${provider.id}`;
    const currentInput = keyInputs[inputKey] || "";

    return (
      <Card className={`relative ${provider.enabled ? 'border-green-500/20 bg-green-50/20' : 'border-gray-200'}`}>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">{provider.name}</CardTitle>
              <CardDescription>
                {provider.models.length} models available
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {provider.has_key && (
                <Badge variant="secondary" className="text-xs">
                  {provider.api_key_count} key(s)
                </Badge>
              )}
              <Switch
                checked={provider.enabled}
                onCheckedChange={(enabled) => toggleProvider(provider.id, enabled)}
                disabled={saving === provider.id || !provider.has_key}
              />
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* API Key Management */}
          <div className="space-y-2">
            <Label>API Key</Label>
            <div className="flex gap-2">
              <Input
                type={showKeys[inputKey] ? "text" : "password"}
                value={currentInput}
                onChange={(e) => setKeyInputs(prev => ({ ...prev, [inputKey]: e.target.value }))}
                placeholder={provider.has_key ? "Enter new key to replace" : "Enter API key"}
                className="font-mono"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => setShowKeys(prev => ({ ...prev, [inputKey]: !prev[inputKey] }))}
              >
                {showKeys[inputKey] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            {provider.has_key && (
              <p className="text-xs text-muted-foreground">
                Current: {provider.api_key_count} key(s) configured (masked for security)
              </p>
            )}
          </div>

          {/* Model List */}
          <div className="space-y-2">
            <Label>Available Models</Label>
            <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
              {provider.models.slice(0, 10).map((model) => (
                <Badge key={model} variant="outline" className="text-xs">
                  {model}
                </Badge>
              ))}
              {provider.models.length > 10 && (
                <Badge variant="secondary" className="text-xs">
                  +{provider.models.length - 10} more
                </Badge>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Button
              onClick={() => saveProviderKey(provider.id, { 
                api_key: currentInput.trim(),
                enabled: true 
              })}
              disabled={!currentInput.trim() || saving === provider.id}
              size="sm"
            >
              {saving === provider.id ? "Saving..." : "Save Key"}
              <Save className="ml-2 h-4 w-4" />
            </Button>
            
            {provider.has_key && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => deleteProviderKey(provider.id)}
                disabled={saving === provider.id}
              >
                Delete
                <Trash2 className="ml-2 h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Status */}
          <div className="flex items-center gap-2 text-sm">
            {provider.enabled ? (
              <>
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-green-600">Available to users</span>
              </>
            ) : provider.has_key ? (
              <>
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <span className="text-amber-600">Key configured but disabled</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4 text-gray-500" />
                <span className="text-gray-500">No API key configured</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!catalog) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500">Failed to load provider catalog</p>
        <Button onClick={loadProviderCatalog} className="mt-2">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">AI Provider Management</h1>
        <p className="text-muted-foreground">
          Configure API keys for AI service providers. Users will automatically use these keys when they select a provider.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          {SERVICE_TABS.map((tab) => {
            const providers = catalog[tab.id as keyof ProviderCatalogResponse] || [];
            const configuredCount = providers.filter(p => p.has_key).length;
            const enabledCount = providers.filter(p => p.enabled).length;
            
            return (
              <TabsTrigger key={tab.id} value={tab.id} className="relative">
                <div className="flex flex-col items-center">
                  <span>{tab.label}</span>
                  <div className="flex gap-1 text-xs">
                    <Badge variant="secondary" className="text-xs px-1">
                      {enabledCount}/{providers.length}
                    </Badge>
                  </div>
                </div>
              </TabsTrigger>
            );
          })}
        </TabsList>

        {SERVICE_TABS.map((tab) => (
          <TabsContent key={tab.id} value={tab.id} className="space-y-4">
            <div className="mb-4">
              <h2 className="text-xl font-semibold">{tab.label} Providers</h2>
              <p className="text-muted-foreground">{tab.description}</p>
            </div>
            
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {(catalog[tab.id as keyof ProviderCatalogResponse] || []).map((provider) => (
                <ProviderCard
                  key={provider.id}
                  provider={provider}
                  serviceType={tab.id}
                />
              ))}
            </div>
            
            {(catalog[tab.id as keyof ProviderCatalogResponse] || []).length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No {tab.label} providers available
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
