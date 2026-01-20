import { defineStore } from 'pinia'
import { ref } from 'vue'
import { accountsApi } from '@/api'
import type { AdminAccount, AccountConfigItem } from '@/types/api'

export const useAccountsStore = defineStore('accounts', () => {
  const accounts = ref<AdminAccount[]>([])
  const isLoading = ref(false)

  async function loadAccounts() {
    isLoading.value = true
    try {
      const response = await accountsApi.list()
      accounts.value = Array.isArray(response)
        ? response
        : response.accounts || []
    } finally {
      isLoading.value = false
    }
  }

  async function deleteAccount(accountId: string) {
    accounts.value = accounts.value.filter(acc => acc.id !== accountId)
    await accountsApi.delete(accountId)
  }

  async function disableAccount(accountId: string) {
    const account = accounts.value.find(acc => acc.id === accountId)
    if (account) account.disabled = true
    await accountsApi.disable(accountId)
  }

  async function enableAccount(accountId: string) {
    const account = accounts.value.find(acc => acc.id === accountId)
    if (account) account.disabled = false
    await accountsApi.enable(accountId)
  }

  async function bulkEnable(accountIds: string[]) {
    accountIds.forEach(id => {
      const account = accounts.value.find(acc => acc.id === id)
      if (account) account.disabled = false
    })
    await Promise.all(accountIds.map(accountId => accountsApi.enable(accountId)))
  }

  async function bulkDisable(accountIds: string[]) {
    accountIds.forEach(id => {
      const account = accounts.value.find(acc => acc.id === id)
      if (account) account.disabled = true
    })
    await Promise.all(accountIds.map(accountId => accountsApi.disable(accountId)))
  }

  async function bulkDelete(accountIds: string[]) {
    accounts.value = accounts.value.filter(acc => !accountIds.includes(acc.id))
    await Promise.all(accountIds.map(accountId => accountsApi.delete(accountId)))
  }

  async function updateConfig(newAccounts: AccountConfigItem[]) {
    await accountsApi.updateConfig(newAccounts)
    await loadAccounts()
  }

  return {
    accounts,
    isLoading,
    loadAccounts,
    deleteAccount,
    disableAccount,
    enableAccount,
    bulkEnable,
    bulkDisable,
    bulkDelete,
    updateConfig,
  }
})
