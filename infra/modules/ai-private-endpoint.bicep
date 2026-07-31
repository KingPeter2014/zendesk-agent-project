// Optional module — wire up a private endpoint for an existing AI Services account.
// Deploy this after the AI Services resource exists.
//
// Usage (in main.bicep or a separate deployment):
//   module aiPe 'modules/ai-private-endpoint.bicep' = {
//     name: 'ai-pe-deploy'
//     params: {
//       location: location
//       projectName: projectName
//       environment: environment
//       aiServicesResourceId: '<AI Services account resource ID>'
//       privateEndpointSubnetId: networkModule.outputs.privateEndpointSubnetId
//       aiServicesDnsZoneId: privateDnsModule.outputs.aiServicesDnsZoneId
//       tags: tags
//     }
//   }

@description('Azure region')
param location string

@description('Project / workload name used as a naming prefix')
param projectName string

@description('Environment name')
param environment string

@description('Resource ID of the Azure AI Services account to connect')
param aiServicesResourceId string

@description('Resource ID of the private-endpoint subnet')
param privateEndpointSubnetId string

@description('Resource ID of the privatelink.cognitiveservices.azure.com DNS zone')
param aiServicesDnsZoneId string

@description('Resource tags')
param tags object

// ── Private Endpoint ──────────────────────────────────────────────────────────

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-${projectName}-${environment}-ai'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${projectName}-${environment}-ai'
        properties: {
          privateLinkServiceId: aiServicesResourceId
          // 'account' is the sub-resource for AI Services / Cognitive Services
          groupIds: ['account']
        }
      }
    ]
  }
}

// ── DNS Zone Group ────────────────────────────────────────────────────────────
// Automatically registers the private endpoint NIC IP in the private DNS zone
// so DNS resolution inside the VNet resolves to the private IP.

resource dnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cognitiveservices'
        properties: {
          privateDnsZoneId: aiServicesDnsZoneId
        }
      }
    ]
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────

output privateEndpointId string = privateEndpoint.id
output privateEndpointName string = privateEndpoint.name
