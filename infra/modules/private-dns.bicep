@description('Resource ID of the VNet to link to each private DNS zone')
param vnetId string

@description('Resource tags')
param tags object

// ── Private DNS zones for Azure AI / Cognitive Services ──────────────────────
//
// A private endpoint NIC gets a FQDN in one of these zones depending on which
// sub-resource (account) the endpoint targets.  All three are created so the
// same VNet works regardless of which AI Services SKU is deployed later.
//
// Zone reference:
//   cognitiveservices.azure.com  → Azure AI Services (multi-service account)
//   openai.azure.com             → Azure OpenAI Service
//   api.cognitive.microsoft.com  → Legacy single-service Cognitive Services

var dnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.api.cognitive.microsoft.com'
]

// ── DNS Zones ─────────────────────────────────────────────────────────────────

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = [
  for zone in dnsZones: {
    name: zone
    location: 'global' // Private DNS zones are always global
    tags: tags
    properties: {}
  }
]

// ── VNet Links ────────────────────────────────────────────────────────────────
// Auto-registration is off — private endpoint DNS records are registered
// automatically by Azure when the endpoint is created; auto-registration is
// for VM hostnames and would pollute the zone.

resource vnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = [
  for (zone, i) in dnsZones: {
    parent: privateDnsZone[i]
    name: 'link-${uniqueString(vnetId, zone)}'
    location: 'global'
    tags: tags
    properties: {
      virtualNetwork: {
        id: vnetId
      }
      registrationEnabled: false
    }
  }
]

// ── Outputs ───────────────────────────────────────────────────────────────────

// Expose the primary AI Services zone ID so callers can reference it when
// creating a private endpoint DNS zone group.
output aiServicesDnsZoneId string = privateDnsZone[0].id
output openAiDnsZoneId string = privateDnsZone[1].id
output cognitiveDnsZoneId string = privateDnsZone[2].id
