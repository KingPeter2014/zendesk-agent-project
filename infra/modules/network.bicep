@description('Azure region')
param location string

@description('Project / workload name used as a naming prefix')
param projectName string

@description('Environment name')
param environment string

@description('VNet address space')
param vnetAddressPrefix string

@description('Address prefix for the workload subnet')
param workloadSubnetPrefix string

@description('Address prefix for the private-endpoint subnet')
param privateEndpointSubnetPrefix string

@description('Resource tags')
param tags object

// ── Name tokens ──────────────────────────────────────────────────────────────

var baseName = '${projectName}-${environment}'

// ── NSG: workload subnet ─────────────────────────────────────────────────────

resource workloadNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'nsg-${baseName}-workload'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'deny-internet-inbound'
        properties: {
          priority: 4000
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
          description: 'Block unsolicited inbound traffic from the internet'
        }
      }
    ]
  }
}

// ── NSG: private-endpoint subnet ─────────────────────────────────────────────
// Private endpoints do not use NSG inbound rules for traffic filtering,
// but an NSG is still attached for audit-trail consistency and future rules.

resource privateEndpointNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'nsg-${baseName}-pe'
  location: location
  tags: tags
  properties: {
    securityRules: []
  }
}

// ── Virtual Network ───────────────────────────────────────────────────────────

resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: 'vnet-${baseName}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [vnetAddressPrefix]
    }
    // Enable VM protection and DDoS basic (Standard requires separate plan resource)
    enableVmProtection: false
    enableDdosProtection: false
    subnets: [
      {
        name: 'snet-workload'
        properties: {
          addressPrefix: workloadSubnetPrefix
          networkSecurityGroup: {
            id: workloadNsg.id
          }
          // Delegate none — general-purpose workload subnet
          delegations: []
          // Service endpoints allow subnet → Azure PaaS without a private endpoint
          // (add as needed; private endpoints are preferred for AI Services)
          serviceEndpoints: []
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          networkSecurityGroup: {
            id: privateEndpointNsg.id
          }
          delegations: []
          serviceEndpoints: []
          // MUST be Disabled to allow private endpoints in this subnet.
          // (UDR-based policies can be re-enabled independently if needed.)
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────

output vnetId string = vnet.id
output vnetName string = vnet.name
output workloadSubnetId string = vnet.properties.subnets[0].id
output privateEndpointSubnetId string = vnet.properties.subnets[1].id
output workloadNsgId string = workloadNsg.id
output privateEndpointNsgId string = privateEndpointNsg.id
