import { api } from './client'
import type { TaskResponse } from './types'

export const tasksApi = {
  /**
   * Get task status by ID
   */
  getTask: async (taskId: string): Promise<TaskResponse> => {
    const { data } = await api.get<TaskResponse>(`/api/tasks/${taskId}`)
    return data
  },

  /**
   * Poll task until completion
   */
  pollTask: async (
    taskId: string,
    options?: {
      interval?: number
      maxAttempts?: number
      onProgress?: (task: TaskResponse) => void
    }
  ): Promise<TaskResponse> => {
    const { interval = 2000, maxAttempts = 60, onProgress } = options || {}
    let attempts = 0

    const poll = async (): Promise<TaskResponse> => {
      const task = await tasksApi.getTask(taskId)

      if (onProgress) {
        onProgress(task)
      }

      if (task.status === 'success' || task.status === 'failure') {
        return task
      }

      attempts++
      if (attempts >= maxAttempts) {
        throw new Error('Task polling timeout exceeded')
      }

      await new Promise((resolve) => setTimeout(resolve, interval))
      return poll()
    }

    return poll()
  },
}
