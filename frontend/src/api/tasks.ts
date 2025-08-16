import { api } from './client'
import type { TaskResponse } from './types'

interface PollOptions {
  interval?: number
  maxAttempts?: number
  onProgress?: (task: TaskResponse) => void
  onTimeout?: (attempts: number) => void
  adaptivePolling?: boolean
}

export const tasksApi = {
  /**
   * Get task status by ID
   */
  getTask: async (taskId: string): Promise<TaskResponse> => {
    const { data } = await api.get<TaskResponse>(`/api/tasks/${taskId}/status`)
    return data
  },

  /**
   * Poll task until completion with adaptive polling and enhanced timeout handling
   */
  pollTask: async (taskId: string, options?: PollOptions): Promise<TaskResponse> => {
    const {
      interval = 2000,
      maxAttempts = 300,
      onProgress,
      onTimeout,
      adaptivePolling = true,
    } = options || {}

    let attempts = 0

    const getPollingInterval = (attemptNumber: number): number => {
      if (!adaptivePolling) {
        return interval
      }

      // Adaptive polling schedule:
      // First 60 attempts (2 minutes): 2s intervals
      // Next 90 attempts (7.5 minutes total): 5s intervals
      // Final 150 attempts (32.5 minutes total): 10s intervals
      if (attemptNumber <= 60) {
        return 2000 // 2 seconds
      } else if (attemptNumber <= 150) {
        return 5000 // 5 seconds
      } else {
        return 10000 // 10 seconds
      }
    }

    const poll = async (): Promise<TaskResponse> => {
      const task = await tasksApi.getTask(taskId)

      if (onProgress) {
        onProgress(task)
      }

      // Check if task completed (success or failure)
      if (task.status === 'success' || task.status === 'failure') {
        return task
      }

      attempts++

      // Handle timeout
      if (attempts >= maxAttempts) {
        if (onTimeout) {
          onTimeout(attempts)
          // Return the last known task state instead of throwing
          return task
        } else {
          throw new Error(
            `Task polling timeout exceeded after ${attempts} attempts (${Math.round((attempts * interval) / 1000)}s)`
          )
        }
      }

      // Wait with adaptive interval
      const currentInterval = getPollingInterval(attempts)
      await new Promise((resolve) => setTimeout(resolve, currentInterval))

      return poll()
    }

    return poll()
  },
}
