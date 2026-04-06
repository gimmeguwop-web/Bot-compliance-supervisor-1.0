import { useEffect } from 'react';
import { 
  Container, 
  Title, 
  Text, 
  Group, 
  Button, 
  Grid, 
  Paper, 
  SimpleGrid,
  Badge,
  Progress,
  Box,
} from '@mantine/core';
import { IconFileCheck, IconUpload, IconClock, IconAlertCircle } from '@tabler/icons-react';
import { useAppStore } from '../store/useAppStore';
import { DocumentUpload } from '../components/DocumentUpload';
import type { DashboardStats } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function Dashboard() {
  const { documents, setDocuments, activeTasks, updateTask, toggleUploadModal } = useAppStore();

  // Mock stats - will be fetched from API in PHASE 5
  const stats: DashboardStats = {
    total_documents: documents.length,
    pending_tasks: activeTasks.filter(t => t.status === 'pending').length,
    completed_tasks: activeTasks.filter(t => t.status === 'completed').length,
    failed_tasks: activeTasks.filter(t => t.status === 'failed').length,
    total_errors: 0,
    total_warnings: 0,
  };

  // Fetch documents on mount
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/documents/`);
        if (response.ok) {
          const data = await response.json();
          setDocuments(data);
        }
      } catch (error) {
        console.error('Failed to fetch documents:', error);
      }
    };

    fetchDocuments();
  }, [setDocuments]);

  return (
    <Container size="xl" py="xl">
      {/* Header */}
      <Group justify="space-between" mb="xl">
        <div>
          <Title order={1}>Панель управления</Title>
          <Text c="dimmed">Мониторинг и управление проверками документов</Text>
        </div>
        <Button 
          leftSection={<IconUpload size={18} />} 
          onClick={toggleUploadModal}
        >
          Загрузить документ
        </Button>
      </Group>

      {/* Stats Cards */}
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="lg" mb="xl">
        <Paper p="md" withBorder>
          <Group gap="sm">
            <IconFileCheck size={28} color="var(--mantine-color-blue-6)" />
            <div>
              <Text size="xs" c="dimmed">Всего документов</Text>
              <Text size="xl" fw={700}>{stats.total_documents}</Text>
            </div>
          </Group>
        </Paper>

        <Paper p="md" withBorder>
          <Group gap="sm">
            <IconClock size={28} color="var(--mantine-color-yellow-6)" />
            <div>
              <Text size="xs" c="dimmed">В очереди</Text>
              <Text size="xl" fw={700}>{stats.pending_tasks}</Text>
            </div>
          </Group>
        </Paper>

        <Paper p="md" withBorder>
          <Group gap="sm">
            <IconFileCheck size={28} color="var(--mantine-color-green-6)" />
            <div>
              <Text size="xs" c="dimmed">Завершено</Text>
              <Text size="xl" fw={700}>{stats.completed_tasks}</Text>
            </div>
          </Group>
        </Paper>

        <Paper p="md" withBorder>
          <Group gap="sm">
            <IconAlertCircle size={28} color="var(--mantine-color-red-6)" />
            <div>
              <Text size="xs" c="dimmed">С ошибками</Text>
              <Text size="xl" fw={700}>{stats.failed_tasks}</Text>
            </div>
          </Group>
        </Paper>
      </SimpleGrid>

      {/* Upload Section */}
      <Paper p="lg" withBorder mb="xl">
        <Title order={3} mb="md">Загрузка документа</Title>
        <DocumentUpload />
      </Paper>

      {/* Active Tasks */}
      <Paper p="lg" withBorder>
        <Title order={3} mb="md">Активные задачи</Title>
        
        {activeTasks.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            Нет активных задач
          </Text>
        ) : (
          <Box>
            {activeTasks.map((task) => (
              <Paper key={task.id} p="md" mb="md" withBorder>
                <Group justify="space-between">
                  <div>
                    <Text fw={500}>Задача #{task.id}</Text>
                    <Text size="sm" c="dimmed">
                      Профиль: {task.profile_id}
                    </Text>
                  </div>
                  <Badge 
                    color={
                      task.status === 'completed' ? 'green' :
                      task.status === 'failed' ? 'red' :
                      task.status === 'processing' ? 'blue' : 'gray'
                    }
                  >
                    {task.status === 'pending' ? 'В очереди' :
                     task.status === 'processing' ? 'Обработка' :
                     task.status === 'completed' ? 'Завершено' : 'Ошибка'}
                  </Badge>
                </Group>
                
                <Progress 
                  value={task.progress} 
                  mt="md" 
                  size="sm"
                  color={task.status === 'failed' ? 'red' : 'blue'}
                />
              </Paper>
            ))}
          </Box>
        )}
      </Paper>
    </Container>
  );
}
