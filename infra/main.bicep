targetScope = 'resourceGroup'

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Project / workload name used as a naming prefix')
param projectName string = 'zendesk-agent'

@description('VNet address space')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('Address prefix for the workload subnet')
param workloadSubnetPrefix string = '10.0.1.0/24'

@description('Address prefix for the private-endpoint subnet')
param privateEndpointSubnetPrefix string = '10.0.2.0/24'

@description('Resource tags applied to every resource')
param tags object = {
  environment: environment
  project: projectName
  managedBy: 'bicep'
}

// ── Modules ──────────────────────────────────────────────────────────────────

module networkModule 'modules/network.bicep' = {
  name: 'network-deploy'
  params: {
    location: location
    projectName: projectName
    environment: environment
    vnetAddressPrefix: vnetAddressPrefix
    workloadSubnetPrefix: workloadSubnetPrefix
    privateEndpointSubnetPrefix: privateEndpointSubnetPrefix
    tags: tags
  }
}

module privateDnsModule 'modules/private-dns.bicep' = {
  name: 'private-dns-deploy'
  params: {
    vnetId: networkModule.outputs.vnetId
    tags: tags
  }
}

// ── Outputs ──────────────────────────────────────────────────────────────────

output vnetId string = networkModule.outputs.vnetId
output vnetName string = networkModule.outputs.vnetName
output workloadSubnetId string = networkModule.outputs.workloadSubnetId
output privateEndpointSubnetId string = networkModule.outputs.privateEndpointSubnetId
output aiServicesDnsZoneId string = privateDnsModule.outputs.aiServicesDnsZoneId
