package com.nomir.forex

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

/** يعمل في الخلفية حتى لو كان التطبيق مغلقاً (أقل فترة يسمح بها أندرويد 15 دقيقة). */
class ScanWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try { Engine.cycle(applicationContext, background = true); Result.success() }
        catch (e: Exception) { Result.retry() }
    }

    companion object {
        private const val NAME = "forex-scan"
        fun schedule(ctx: Context, minutes: Int) {
            val req = PeriodicWorkRequestBuilder<ScanWorker>(maxOf(15, minutes).toLong(), TimeUnit.MINUTES)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(NAME, ExistingPeriodicWorkPolicy.UPDATE, req)
        }
    }
}
