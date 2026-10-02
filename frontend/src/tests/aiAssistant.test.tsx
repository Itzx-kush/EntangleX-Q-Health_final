import {describe,expect,it,vi} from 'vitest';
import {fireEvent,render,screen} from '@testing-library/react';
import {AiAssistantPage} from '../pages/AiAssistantPage';
import {AiProvider} from '../contexts/AiContext';

const {aiChat}=vi.hoisted(()=>({aiChat:vi.fn()}));
vi.mock('../lib/api',()=>({qh:{aiChat}}}));

describe('AI assistant UI',()=>{
  it('renders the research assistant and sends an example prompt through the shared API',async()=>{
    aiChat.mockResolvedValue({reply:'The hybrid workflow combines classical and quantum components.'});
    render(<AiProvider><AiAssistantPage/></AiProvider>);

    expect(screen.getByText('EntangleX AI Assistant')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'What is EntangleX Q-Health?'}));

    expect(aiChat).toHaveBeenCalledWith({
      message:'What is EntangleX Q-Health?',
      conversation:[],
    });
    expect(await screen.findByText(/The hybrid workflow combines/)).toBeInTheDocument();
  });
});
