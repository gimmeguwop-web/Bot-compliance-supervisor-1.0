import { useState, useCallback } from 'react';
import { Group, Button, Text, Progress, Box } from '@mantine/core';
import { IconUpload, IconFileCheck, IconX } from '@tabler/icons-react';
import { useAppStore } from '../store/useAppStore';
import type { UploadResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function DocumentUpload() {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { toggleUploadModal, setLoading, setError, addTask } = useAppStore();

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Только PDF файлы поддерживаются');
      return;
    }

    setUploading(true);
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('profile_id', 'gost_2.104_basic');

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка загрузки');
      }

      const data: UploadResponse = await response.json();
      
      // Add task to store
      addTask({
        id: data.task_id,
        document_id: data.document_id,
        profile_id: 'gost_2.104_basic',
        status: 'pending',
        progress: 0,
      });

      console.log('Upload successful:', data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
    } finally {
      setUploading(false);
      setLoading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, [handleFile]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  }, [handleFile]);

  return (
    <Box
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      p="xl"
      style={{
        border: `2px dashed ${dragActive ? 'var(--mantine-color-blue-6)' : 'var(--mantine-color-gray-3)'}`,
        borderRadius: 'var(--mantine-radius-md)',
        textAlign: 'center',
        padding: 'var(--mantine-spacing-xl)',
      }}
    >
      <IconUpload size={48} color="var(--mantine-color-dimmed)" stroke={1.5} />
      
      <Text mt="md" fw={500}>
        Перетащите PDF файл сюда или кликните для выбора
      </Text>
      
      <Text c="dimmed" size="sm" mt="xs">
        Поддерживаются файлы до 50MB
      </Text>

      <input
        type="file"
        id="file-upload"
        accept=".pdf"
        onChange={handleChange}
        style={{ display: 'none' }}
      />

      <Group justify="center" mt="lg">
        <Button
          component="label"
          htmlFor="file-upload"
          leftSection={<IconUpload size={18} />}
          loading={uploading}
        >
          Выбрать файл
        </Button>
      </Group>

      {uploading && (
        <Box mt="lg">
          <Progress indeterminate size="sm" />
          <Text size="sm" c="dimmed" mt="xs">
            Загрузка файла...
          </Text>
        </Box>
      )}
    </Box>
  );
}
