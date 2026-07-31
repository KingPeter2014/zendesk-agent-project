using './main.bicep'

// ── Required ──────────────────────────────────────────────────────────────────
param environment = 'dev'
param projectName = 'zendesk-agent'

// ── Optional overrides (defaults in main.bicep are used when omitted) ─────────
// param location = 'eastus'
// param vnetAddressPrefix = '10.0.0.0/16'
// param workloadSubnetPrefix = '10.0.1.0/24'
// param privateEndpointSubnetPrefix = '10.0.2.0/24'

param tags = {
  environment: 'dev'
  project: 'zendesk-agent'
  managedBy: 'bicep'
  costCenter: 'eng'
}
